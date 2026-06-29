import sqlite3
import cv2
import winsound
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

from test_video import process_frame
from database import init_db, log_alert, mark_false_alarm, count_after_hours, DATABASE

app = Flask(__name__)
app.secret_key = 'super_secure_surveillance_key_2026'

# Initialize database on startup
init_db()

# --- Thresholds & Cooldowns ---
last_alert_time = 0
last_after_hours_log = 0
ALERT_COOLDOWN = 5.0  

CLOSING_HOUR = 17
REPEAT_THRESHOLD = 3
CROWD_THRESHOLD = 3

def generate_frames():
    global last_alert_time, last_after_hours_log
    camera = cv2.VideoCapture(0)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame, alert_triggered, alert_message, alert_type, alert_conf, person_count = process_frame(frame)
            
            # --- CONTEXT-AWARE: After-hours rules ---
            current_hour = datetime.now().hour
            if current_hour >= CLOSING_HOUR:
                if person_count >= CROWD_THRESHOLD:
                    alert_triggered = True
                    alert_message = "ALERT: Crowd detected after working hours!"
                    alert_type = "after-hours-crowd"
                    alert_conf = 1.0
                elif person_count > 0:
                    if time.time() - last_after_hours_log > 10:
                        log_alert("after-hours", 1.0)
                        last_after_hours_log = time.time()
                        times_seen = count_after_hours()
                        if times_seen >= REPEAT_THRESHOLD:
                            alert_triggered = True
                            alert_message = "ALERT: Repeated after-hours pattern!"
                            alert_type = "after-hours-pattern"
                            alert_conf = 1.0

            # --- System Alert Handling ---
            if alert_triggered:
                cv2.putText(frame, alert_message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                current_time = time.time()
                if current_time - last_alert_time > ALERT_COOLDOWN:
                    if alert_type not in ("", "after-hours"): 
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

# --- NEW ROUTING LOGIC ---

@app.route('/')
def index():
    # If already logged in, go straight to dashboard
    if 'username' in session: 
        return redirect(url_for('dashboard'))
    # Otherwise, show the new Portal Selector page
    return render_template('index.html')

@app.route('/login/<role_type>', methods=['GET', 'POST'])
def login(role_type):
    role_type = role_type.capitalize() # Forces 'admin' to 'Admin'
    
    # Security check: Only allow valid roles in the URL
    if role_type not in ['Admin', 'Operator']:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                # Verify their actual role matches the portal they tried to log into
                if user['role'].lower() == role_type.lower():
                    session['username'] = user['username']
                    session['role'] = user['role']
                    return redirect(url_for('dashboard'))
                else:
                    flash(f"Access Denied: This account does not have {role_type} privileges.", "error")
            else:
                flash("Invalid username or password.", "error")
                
    return render_template('login.html', role_type=role_type)

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
        flash("Account created! Please log in to the Operator portal.", "success")
        return redirect(url_for('login', role_type='operator'))
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('index'))
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
        <td style="font-size: 0.8rem; color: #64748b;">{{ alert.timestamp.split()[1] if alert.timestamp else '' }}</td>
        <td style="font-weight: bold; text-transform: capitalize;">{{ alert.alert_type.replace('-', ' ') }}</td>
        <td style="font-size: 0.85rem;">{{ "%.0f"|format(alert.confidence * 100) }}%</td>
        <td>
            {% if alert.is_false_alarm %}
                <span style="color: #64748b; font-weight: bold; font-size: 0.85rem;">Dismissed</span>
            {% else %}
                <span style="color: #dc2626; font-weight: bold; font-size: 0.85rem;">Active</span>
            {% endif %}
        </td>
        <td>
            {% if not alert.is_false_alarm %}
            <form action="{{ url_for('flag_false_alarm', alert_id=alert.id) }}" method="POST" style="margin: 0;">
                <button type="submit" class="btn" style="background:#64748b; padding: 4px 8px; font-size: 0.75rem;">Mark False</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr>
        <td colspan="5" style="color: #64748b; text-align: center; padding: 30px;">No active security events logged.</td>
    </tr>
    {% endfor %}
    """
    return render_template_string(row_template, alerts=alerts)

@app.route('/mark_false_alarm/<int:alert_id>', methods=['POST'])
def flag_false_alarm(alert_id):
    if 'username' not in session: return redirect(url_for('index'))
    mark_false_alarm(alert_id)
    return redirect(url_for('dashboard'))

@app.route('/users')
def users():
    if 'username' not in session: return redirect(url_for('index'))
    
    current_role = session.get('role', '')
    if not current_role or current_role.lower() != 'admin':
        flash("Access Denied: Administrator privileges required.", "error")
        return redirect(url_for('dashboard'))
        
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
        all_users = cursor.fetchall()
        
    return render_template('users.html', username=session['username'], role=current_role, users=all_users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)