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
                role TEXT DEFAULT 'Operator'
            )
        ''')
        
        # 2. Create Alerts Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                alert_type TEXT,
                confidence REAL,
                is_false_alarm INTEGER DEFAULT 0
            )
        ''')
        
        # 3. Ensure Admin Account Exists
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('admin123')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'Admin')", ('admin', hashed_pw))
        
        conn.commit()

def log_alert(alert_type, confidence):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT INTO alerts (timestamp, alert_type, confidence) VALUES (?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), alert_type, confidence)
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

# ============ ADD THESE TO database.py ============

def init_events():
    conn = sqlite3.connect(DATABASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT,           -- 'YYYY-MM-DD'
            name TEXT,
            start_hour INTEGER,        -- 0-23, when the event starts
            end_hour INTEGER,          -- 0-23, when it ends
            expected_crowd INTEGER     -- how many people is normal during it
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