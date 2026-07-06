import sqlite3
import cv2
import winsound
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from ultralytics import YOLO

from database import init_db, log_alert, mark_false_alarm, count_after_hours, DATABASE
from violence_detector import ViolenceDetector          # YOUR temporal violence model
from context_engine import ThreatAssessor, IGNORE, LOG, NOTIFY, ALARM   # YOUR context engine
try:
    from email_alert import send_email_alert          # emails the logged-in operator
except Exception:
    send_email_alert = None

app = Flask(__name__)
app.secret_key = 'super_secure_surveillance_key_2026'
init_db()

# ----------------- INPUT SOURCE -----------------
USE_WEBCAM = True
VIDEO_PATH = "fight.mp4"

# ----------------- DETECTION SETUP (loaded once) -----------------
general_model = YOLO("yolov8s.pt")                                    # person detection + tracking
weapon_model = YOLO("best.pt")                                        # gun/knife detection
violence_detector = ViolenceDetector("violence_mobilenet_lstm.pt")   # temporal violence model
assessor = ThreatAssessor()                                          # context-aware decision engine

WEAPON_KEYWORDS = ("gun", "knife", "knive", "pistol", "rifle", "handgun", "shotgun", "weapon", "blade")
ACTION_COOLDOWN = 5.0
last_action = {}
DISMISS_SECRET = "kec_surveillance_2026"   # MUST match email_alert.py
TIER_COLOR = {LOG: (0, 255, 255), NOTIFY: (0, 165, 255), ALARM: (0, 0, 255)}


def _should_act(alert_type):
    """Anti-spam: only log/beep once per ACTION_COOLDOWN seconds per alert type."""
    now = time.time()
    if now - last_action.get(alert_type, 0) >= ACTION_COOLDOWN:
        last_action[alert_type] = now
        return True
    return False


def _detect_signals(img):
    """Run detectors, draw boxes, return RAW signals for the engine."""
    person_results = general_model.track(img, classes=[0], conf=0.5, persist=True, verbose=False)[0]
    img = person_results.plot()
    person_count = len(person_results.boxes)
    track_ids = (person_results.boxes.id.int().tolist()
                 if person_results.boxes.id is not None else [])

    weapon_results = weapon_model(img, conf=0.5, verbose=False)[0]
    img = weapon_results.plot()
    weapons = []
    for box in weapon_results.boxes:
        name = weapon_model.names[int(box.cls[0])].lower()
        if any(k in name for k in WEAPON_KEYWORDS):
            weapons.append((name, float(box.conf[0])))
    return img, person_count, track_ids, weapons


def generate_frames(operator_email=None):
    """Live feed WITH violence detection + context-aware threat assessment."""
    camera = cv2.VideoCapture(0) if USE_WEBCAM else cv2.VideoCapture(VIDEO_PATH)
    while True:
        success, frame = camera.read()
        if not success:
            break

        # 1) violence score from the temporal model (clean frame)
        is_violent, violence_prob = violence_detector.update(frame)

        # 2) detectors -> raw signals (also draws the boxes)
        img, person_count, track_ids, weapons = _detect_signals(frame)

        # 3) THE BRAIN: context engine combines all signals -> a response tier
        tier, alert_type, message, conf = assessor.assess(
            violence_prob=violence_prob, weapons=weapons,
            person_count=person_count, track_ids=track_ids,
            current_hour=datetime.now().hour)

        # 4) act on the tier
        if tier != IGNORE:
            cv2.putText(img, message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, TIER_COLOR.get(tier, (0, 0, 255)), 2)
            if _should_act(alert_type):
                new_id = log_alert(alert_type, conf)          # record to DB, get its id
                if tier == ALARM:
                    try:
                        winsound.Beep(1000, 200)              # siren on real threats
                    except Exception:
                        pass
                    if operator_email and send_email_alert:   # email the logged-in operator
                        send_email_alert(operator_email, message, new_id)

        # live violence score readout (green = calm, red = violent)
        cv2.putText(img, f"Violence: {violence_prob:.2f}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255) if is_violent else (0, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    camera.release()


# ================= SUDARSHAN'S ROUTES (unchanged) =================

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login/<role_type>', methods=['GET', 'POST'])
def login(role_type):
    role_type = role_type.capitalize()
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
    if 'username' not in session:
        return redirect(url_for('index'))
    run_live = request.args.get('live', 'false') == 'true'
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 15")
        alerts = cursor.fetchall()
    return render_template('dashboard.html', username=session['username'], role=session['role'], alerts=alerts, run_live=run_live)


@app.route('/video_feed')
def video_feed():
    if 'username' not in session:
        return "Unauthorized", 401
    operator_email = None
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT email FROM users WHERE username=?", (session['username'],)).fetchone()
        if row:
            operator_email = row['email']
    return Response(generate_frames(operator_email), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_alerts')
def get_alerts():
    if 'username' not in session:
        return "Unauthorized", 401
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
    if 'username' not in session:
        return redirect(url_for('index'))
    mark_false_alarm(alert_id)
    return redirect(url_for('dashboard'))


@app.route('/users')
def users():
    if 'username' not in session:
        return redirect(url_for('index'))
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



@app.route('/dismiss/<int:alert_id>/<token>')
def dismiss_alert(alert_id, token):
    """One-click 'false alarm' button from the alert email lands here."""
    if token != DISMISS_SECRET:
        return "Invalid or expired dismissal link.", 403
    mark_false_alarm(alert_id)
    confirm = """
    <div style="font-family:Arial,sans-serif; max-width:420px; margin:60px auto; text-align:center;
                border:1px solid #e0e0e0; border-radius:10px; padding:30px;">
      <div style="font-size:42px; color:#188038;">&#10004;</div>
      <h2 style="color:#202124;">Alert #{{ aid }} dismissed</h2>
      <p style="color:#5f6368;">This event has been marked as a false alarm.<br>You can close this window.</p>
    </div>
    """
    return render_template_string(confirm.replace("{{ aid }}", str(alert_id)))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True, host='0.0.0.0')