import sqlite3
import cv2
import winsound
import time
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

from test_video import process_frame
from database import init_db, log_alert, mark_false_alarm, DATABASE

app = Flask(__name__)
app.secret_key = 'super_secure_surveillance_key_2026'

# Initialize database on startup
init_db()

# Alert Cooldown (Wait 5 seconds before logging the exact same event again)
last_alert_time = 0
ALERT_COOLDOWN = 5.0  

def generate_frames():
    global last_alert_time
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame, alert_triggered, alert_message, alert_type, alert_conf = process_frame(frame)
            
            if alert_triggered:
                current_time = time.time()
                if current_time - last_alert_time > ALERT_COOLDOWN:
                    log_alert(alert_type, alert_conf)
                    last_alert_time = current_time
                    try:
                        winsound.Beep(1000, 200)
                    except:
                        pass

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    camera.release()

@app.route('/')
def index():
    if 'username' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            if cursor.fetchone():
                flash("Username already exists.", "error")
                return redirect(url_for('signup'))
            hashed_pw = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'Operator')", (username, hashed_pw))
            conn.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    run_live = request.args.get('live', 'false') == 'true'
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 15")
        alerts = cursor.fetchall()
        
    return render_template('dashboard.html', username=session['username'], role=session['role'], alerts=alerts, run_live=run_live)

@app.route('/video_feed')
def video_feed():
    if 'username' not in session: return "Unauthorized", 401
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_alerts')
def get_alerts():
    if 'username' not in session: return "Unauthorized", 401
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 15")
        alerts = cursor.fetchall()
        
    row_template = """
    {% for alert in alerts %}
    <tr class="{% if alert.is_false_alarm %}false-alarm-row{% else %}alert-row{% endif %}">
        <td style="font-size: 0.85rem; color: #64748b;">{{ alert.timestamp }}</td>
        <td style="font-weight: bold; text-transform: capitalize;">{{ alert.alert_type }}</td>
        <td>{{ "%.1f"|format(alert.confidence * 100) }}%</td>
        <td>
            {% if alert.is_false_alarm %}
                <span style="color: #64748b; font-weight: bold;">False Alarm</span>
            {% else %}
                <span style="color: #dc2626; font-weight: bold;">Confirmed</span>
            {% endif %}
        </td>
        <td>
            {% if not alert.is_false_alarm %}
            <form action="{{ url_for('flag_false_alarm', alert_id=alert.id) }}" method="POST" style="margin: 0;">
                <button type="submit" class="btn" style="background:#64748b; padding: 6px 10px; font-size: 0.8rem;">Mark False</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr><td colspan="5" style="color: #64748b; text-align: center;">No security events triggered.</td></tr>
    {% endfor %}
    """
    return render_template_string(row_template, alerts=alerts)

@app.route('/mark_false_alarm/<int:alert_id>', methods=['POST'])
def flag_false_alarm(alert_id):
    if 'username' not in session: return redirect(url_for('login'))
    mark_false_alarm(alert_id)
    return redirect(url_for('dashboard'))

@app.route('/users')
def users():
    if 'username' not in session: return redirect(url_for('login'))
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
    # Threaded=True prevents the video feed from freezing the web app!
    app.run(debug=True, port=5000, threaded=True)