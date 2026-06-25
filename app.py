import os
import sqlite3
import cv2
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash
from werkzeug.security import generate_password_hash, check_password_hash

from test_video import process_frame

app = Flask(__name__)
app.secret_key = 'surveillance_secret_key_123'
DATABASE = 'database.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'operator'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message TEXT NOT NULL
            )
        ''')
        
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('admin123')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'Admin')", ('admin', hashed_pw))
        conn.commit()

init_db()

def generate_frames():
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame, alert_triggered, alert_message = process_frame(frame)
            
            if alert_triggered:
                with sqlite3.connect(DATABASE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO alerts (message) VALUES (?)", (alert_message,))
                    conn.commit()

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    camera.release()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            if cursor.fetchone():
                flash("Username already exists. Please choose another.", "error")
                return redirect(url_for('signup'))
            
            hashed_pw = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'Operator')", (username, hashed_pw))
            conn.commit()
            
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['username'] = user['username']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid username or password.", "error")
                
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    run_live = request.args.get('live', 'false') == 'true'
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 10")
        alerts = cursor.fetchall()
        
    return render_template('dashboard.html', username=session['username'], role=session['role'], alerts=alerts, run_live=run_live)

@app.route('/video_feed')
def video_feed():
    if 'username' not in session:
        return "Unauthorized", 401
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/users')
def users():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') != 'Admin':
        flash("Access Denied: Administrator privileges required.", "error")
        return redirect(url_for('dashboard'))
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
        all_users = cursor.fetchall()
        
    return render_template('users.html', username=session['username'], users=all_users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)