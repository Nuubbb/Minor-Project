import re
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DATABASE = "database.db"


def _slugify_username(name):
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "resident"


def _unique_username(cursor, base):
    username = base
    n = 2
    while cursor.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        username = f"{base}{n}"
        n += 1
    return username

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # 1. Create Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'Operator',
            phone TEXT,
            lat REAL,
            lng REAL
        )
        ''')
        # Existing databases created before phone/lat/lng existed -- add them
        # in place (SQLite has no "ADD COLUMN IF NOT EXISTS", so check first).
        existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}
        for col, coltype, default in (("phone", "TEXT", None), ("lat", "REAL", None), ("lng", "REAL", None), ("status", "TEXT", "'approved'")):
            if col not in existing_cols:
                if default:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype} DEFAULT {default}")
                else:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype}")

        # 2. Create Deleted Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS deleted_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_user_id INTEGER,
            username TEXT,
            email TEXT,
            role TEXT,
            deleted_at TEXT
        )
        ''')
        
        # 3. Create Alerts Table (NEW: added operator_username)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            alert_type TEXT,
            confidence REAL,
            is_false_alarm INTEGER DEFAULT 0,
            operator_username TEXT DEFAULT 'system'
        )
        ''')
        
        # 4. Ensure Admin Account Exists
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('admin123')
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, 'Admin')", ('admin', hashed_pw, 'admin@system.local'))

        # 5. Device Location -- single row (id=1) holding the real, admin-set
        # location of this camera/device. Replaces the old hardcoded
        # config.py placeholder. Created before the community migration below
        # so its lat/lng can be used to seed nearby resident pins.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_location (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            label TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
        ''')
        cursor.execute("SELECT COUNT(*) FROM device_location")
        if cursor.fetchone()[0] == 0:
            from config import DEVICE_LOCATION as _default_location
            cursor.execute(
                "INSERT INTO device_location (id, label, lat, lng) VALUES (1, ?, ?, ?)",
                (_default_location["label"], _default_location["lat"], _default_location["lng"])
            )
        device_row = cursor.execute("SELECT lat, lng FROM device_location WHERE id=1").fetchone()
        base_lat, base_lng = device_row[0], device_row[1]

        # 6. Community members are real logged-in accounts (role='Resident'
        # on `users`), not a separate passive-contact table -- this is what
        # lets an owner get a real push notification and validate a peer
        # report themselves. Migrate any rows from the old `community_members`
        # table (used before this feature had login) into `users`, then drop it.
        old_table_exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='community_members'"
        ).fetchone()
        if old_table_exists:
            offsets = [(0.0025, 0.0012), (-0.0018, 0.0022), (0.0012, -0.0028), (-0.0022, -0.0016), (0.0028, 0.0006)]
            old_members = cursor.execute("SELECT name, email, phone FROM community_members").fetchall()
            for i, (name, email, phone) in enumerate(old_members):
                username = _unique_username(cursor, _slugify_username(name))
                dlat, dlng = offsets[i % len(offsets)]
                cursor.execute(
                    "INSERT INTO users (username, password, email, role, phone, lat, lng) VALUES (?, ?, ?, 'Resident', ?, ?, ?)",
                    (username, generate_password_hash('resident123'), email, phone,
                     base_lat + dlat, base_lng + dlng)
                )
            cursor.execute("DROP TABLE community_members")

        # 7. If there are still no Residents at all (fresh install, no old
        # table to migrate from), seed the same dummy community directly.
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='Resident'")
        if cursor.fetchone()[0] == 0:
            dummy_community = [
                ("Asha Gurung",   "asha.gurung@example.com",   "+977-9800000001"),
                ("Bikash Thapa",  "bikash.thapa@example.com",  "+977-9800000002"),
                ("Nisha Rai",     "nisha.rai@example.com",     "+977-9800000003"),
                ("Prakash Shrestha", "prakash.shrestha@example.com", "+977-9800000004"),
                ("Sunita KC",     "sunita.kc@example.com",     "+977-9800000005"),
            ]
            offsets = [(0.0025, 0.0012), (-0.0018, 0.0022), (0.0012, -0.0028), (-0.0022, -0.0016), (0.0028, 0.0006)]
            for i, (name, email, phone) in enumerate(dummy_community):
                username = _unique_username(cursor, _slugify_username(name))
                dlat, dlng = offsets[i % len(offsets)]
                cursor.execute(
                    "INSERT INTO users (username, password, email, role, phone, lat, lng) VALUES (?, ?, ?, 'Resident', ?, ?, ?)",
                    (username, generate_password_hash('resident123'), email, phone,
                     base_lat + dlat, base_lng + dlng)
                )

        # 8. Peer Reports -- a resident flagging another resident's (simulated)
        # camera as suspicious. Pending until the house owner validates it;
        # a confirmed report becomes a normal `alerts` row (via log_alert)
        # so it flows through the existing Take-a-Look / Notify-Community
        # pipeline instead of needing a parallel one.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS peer_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_user_id INTEGER NOT NULL,
            owner_user_id INTEGER NOT NULL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            timestamp TEXT,
            resolved_at TEXT
        )
        ''')

    conn.commit()


# NEW: Updated to accept and log the operator's username
def log_alert(alert_type, confidence, operator_username="system"):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "INSERT INTO alerts (timestamp, alert_type, confidence, operator_username) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), alert_type, confidence, operator_username)
        )
        conn.commit()
        return cursor.lastrowid

def mark_false_alarm(alert_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE alerts SET is_false_alarm = 1 WHERE id = ?", (alert_id,))
        conn.commit()

def count_after_hours():
    with sqlite3.connect(DATABASE) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alert_type = 'after-hours'"
        ).fetchone()[0]
    return count


def init_events():
    conn = sqlite3.connect(DATABASE)
    
    # 1. Create Active Events Table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT, -- 'YYYY-MM-DD'
        name TEXT,
        start_hour INTEGER, 
        end_hour INTEGER, 
        expected_crowd INTEGER 
    )
    """)
    
    # NEW: Create Deleted Events Table for archiving
    conn.execute("""
    CREATE TABLE IF NOT EXISTS deleted_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_event_id INTEGER,
        event_date TEXT,
        name TEXT,
        start_hour INTEGER,
        end_hour INTEGER,
        expected_crowd INTEGER,
        deleted_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()


def add_event(event_date, name, start_hour, end_hour, expected_crowd):
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        "INSERT INTO events (event_date, name, start_hour, end_hour, expected_crowd) VALUES (?, ?, ?, ?, ?)",
        (event_date, name, int(start_hour), int(end_hour), int(expected_crowd))
    )
    conn.commit()
    conn.close()


def get_all_events():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM events ORDER BY event_date DESC").fetchall()
    conn.close()
    return rows


def delete_user(user_id, requester_username):
    """Archive + delete a user. Returns ('ok', user_dict) / ('self', None) / ('not_found', None)."""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE id=?", (user_id,))
        user_to_delete = cursor.fetchone()

        if not user_to_delete:
            return "not_found", None

        if user_to_delete["username"] == requester_username:
            return "self", None

        cursor.execute('''
            INSERT INTO deleted_users (original_user_id, username, email, role, deleted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_to_delete["id"], user_to_delete["username"], user_to_delete["email"],
              user_to_delete["role"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return "ok", dict(user_to_delete)


def delete_event(event_id):
    """Archive + delete an event. Returns ('ok', event_dict) / ('not_found', None)."""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, event_date, name, start_hour, end_hour, expected_crowd FROM events WHERE id=?",
            (event_id,)
        )
        event_to_delete = cursor.fetchone()

        if not event_to_delete:
            return "not_found", None

        cursor.execute('''
            INSERT INTO deleted_events (original_event_id, event_date, name, start_hour, end_hour, expected_crowd, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_to_delete["id"], event_to_delete["event_date"], event_to_delete["name"],
              event_to_delete["start_hour"], event_to_delete["end_hour"], event_to_delete["expected_crowd"],
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
        conn.commit()
        return "ok", dict(event_to_delete)


def get_community_members():
    """Residents (community members) are real `users` accounts (role='Resident')."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, username AS name, email, phone, lat, lng FROM users WHERE role='Resident' ORDER BY username"
    ).fetchall()
    conn.close()
    return rows


def add_community_member(name, email, phone=None, lat=None, lng=None):
    """Creates a new Resident account. Returns the generated username and default password."""
    default_password = "resident123"
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        username = _unique_username(cursor, _slugify_username(name))
        cursor.execute(
            "INSERT INTO users (username, password, email, role, phone, lat, lng) VALUES (?, ?, ?, 'Resident', ?, ?, ?)",
            (username, generate_password_hash(default_password), email, phone, lat, lng)
        )
        conn.commit()
        return username, default_password


def delete_community_member(member_id):
    """Archive + delete a Resident account (same pattern as delete_user)."""
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users WHERE id=? AND role='Resident'", (member_id,))
        member = cursor.fetchone()
        if not member:
            return "not_found"

        cursor.execute('''
            INSERT INTO deleted_users (original_user_id, username, email, role, deleted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (member["id"], member["username"], member["email"], member["role"],
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        cursor.execute("DELETE FROM users WHERE id=?", (member_id,))
        conn.commit()
        return "ok"


def get_device_location():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT label, lat, lng FROM device_location WHERE id=1").fetchone()
    conn.close()
    return dict(row)


def update_device_location(label, lat, lng):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "UPDATE device_location SET label=?, lat=?, lng=? WHERE id=1",
            (label, lat, lng)
        )
        conn.commit()


def get_active_event():
    """If RIGHT NOW falls inside a scheduled event, return (name, expected_crowd); else None."""
    from datetime import datetime
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    hour = now.hour
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT name, expected_crowd FROM events "
        "WHERE event_date=? AND start_hour<=? AND end_hour>?",
        (today, hour, hour)
    ).fetchone()
    conn.close()
    return (row["name"], row["expected_crowd"]) if row else None


def create_peer_report(reporter_user_id, owner_user_id, message=None):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "INSERT INTO peer_reports (reporter_user_id, owner_user_id, message, timestamp) VALUES (?, ?, ?, ?)",
            (reporter_user_id, owner_user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return cursor.lastrowid


def get_pending_reports_for(owner_user_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT pr.*, u.username AS reporter_username
           FROM peer_reports pr JOIN users u ON u.id = pr.reporter_user_id
           WHERE pr.owner_user_id=? AND pr.status='pending'
           ORDER BY pr.timestamp DESC""",
        (owner_user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_peer_report(report_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT pr.*, u.username AS reporter_username, o.username AS owner_username
           FROM peer_reports pr
           JOIN users u ON u.id = pr.reporter_user_id
           JOIN users o ON o.id = pr.owner_user_id
           WHERE pr.id=?""",
        (report_id,)
    ).fetchone()
    conn.close()
    return row


def resolve_peer_report(report_id, confirmed):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "UPDATE peer_reports SET status=?, resolved_at=? WHERE id=? AND status='pending'",
            ("confirmed" if confirmed else "dismissed",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), report_id)
        )
        conn.commit()
        return "ok" if cursor.rowcount else "not_found"