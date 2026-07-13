import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DATABASE = "database.db"

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
            role TEXT DEFAULT 'Operator'
        )
        ''')

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
            
    conn.commit()


# NEW: Updated to accept and log the operator's username
def log_alert(alert_type, confidence, operator_username="system"):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT INTO alerts (timestamp, alert_type, confidence, operator_username) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), alert_type, confidence, operator_username)
        )
        conn.commit()

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