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