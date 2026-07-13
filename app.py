import sqlite3
import cv2
import threading
import time
import platform
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from ultralytics import YOLO

from database import (init_db, log_alert, mark_false_alarm, count_after_hours, DATABASE,
                      init_events, add_event, get_all_events, get_active_event)
from violence_detector import ViolenceDetector          # YOUR temporal violence model
from context_engine import ThreatAssessor, IGNORE, LOG, NOTIFY, ALARM   # YOUR context engine
try:
    from email_alert import send_email_alert          # emails the logged-in operator
except Exception:
    send_email_alert = None

app = Flask(__name__)
app.secret_key = 'super_secure_surveillance_key_2026'
init_db()
init_events()

# ----------------- INPUT SOURCE -----------------
USE_WEBCAM = True
VIDEO_PATH = "fight.mp4"

# ----------------- DETECTION SETUP (loaded once) -----------------
general_model = YOLO("yolov8n.pt")                                    # person detection (nano = faster)
weapon_model = YOLO("best.pt")                                        # gun/knife detection
violence_detector = ViolenceDetector("violence_mobilenet_lstm.pt")   # temporal violence model
assessor = ThreatAssessor()                                          # context-aware decision engine

WEAPON_KEYWORDS = ("gun", "knife", "knive", "pistol", "rifle", "handgun", "shotgun", "weapon", "blade")
ACTION_COOLDOWN = 5.0
last_action = {}
_last_email = {"t": 0.0}   # throttle emails: at most one per minute
DISMISS_SECRET = "kec_surveillance_2026"   # MUST match email_alert.py
TIER_COLOR = {LOG: (0, 255, 255), NOTIFY: (0, 165, 255), ALARM: (0, 0, 255)}


def trigger_audio_alarm():
    """Cross-platform function to play an alarm sound."""
    try:
        current_os = platform.system()
        if current_os == "Windows":
            import winsound
            winsound.Beep(1000, 200)
        elif current_os == "Darwin": # Mac OS
            # The '&' runs it in the background so it doesn't freeze the video feed
            os.system('afplay /System/Library/Sounds/Glass.aiff &')
        else: # Linux or other
            print('\a') # Triggers terminal bell
    except Exception as e:
        print(f"[audio] skip: {e}")


def _should_act(alert_type):
    """Anti-spam: only log/beep once per ACTION_COOLDOWN seconds per alert type."""
    now = time.time()
    if now - last_action.get(alert_type, 0) >= ACTION_COOLDOWN:
        last_action[alert_type] = now
        return True
    return False


def _detect_persons(frame):
    """Fast person detection + tracking (nano model). Runs often."""
    boxes, count, ids = [], 0, []
    try:
        pr = general_model.track(frame, classes=[0], conf=0.5, persist=True, verbose=False, imgsz=320)[0]
        count = len(pr.boxes)
        ids = pr.boxes.id.int().tolist() if pr.boxes.id is not None else []
        id_list = ids if ids else [None] * count
        for i, xyxy in enumerate(pr.boxes.xyxy.cpu().numpy().astype(int)):
            x1, y1, x2, y2 = xyxy
            pid = id_list[i] if i < len(id_list) else None
            label = f"id:{pid} person" if pid is not None else "person"
            boxes.append((x1, y1, x2, y2, label, (0, 255, 0)))
    except Exception as e:
        print("[person det] skip:", e)
    return boxes, count, ids


def _detect_weapons(frame):
    """Weapon detection (heavier model). Runs RARELY -- weapons are rare + mostly static."""
    boxes, weapons = [], []
    try:
        wr = weapon_model(frame, conf=0.5, verbose=False, imgsz=320)[0]
        for xyxy, cls, conf in zip(wr.boxes.xyxy.cpu().numpy().astype(int),
                                   wr.boxes.cls.cpu().numpy().astype(int),
                                   wr.boxes.conf.cpu().numpy()):
            name = weapon_model.names[int(cls)]
            if any(k in name.lower() for k in WEAPON_KEYWORDS):   # only real weapons
                x1, y1, x2, y2 = xyxy
                boxes.append((x1, y1, x2, y2, f"{name} {conf:.2f}", (0, 0, 255)))
                weapons.append((name.lower(), float(conf)))
    except Exception as e:
        print("[weapon det] skip:", e)
    return boxes, weapons


def _draw_boxes(img, boxes):
    """Draw cached boxes onto a frame (used on skipped frames)."""
    for (x1, y1, x2, y2, label, color) in boxes:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, max(15, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return img


_event_cache = {"checked": 0.0, "active": None}
def current_event():
    """Return (name, expected_crowd) if an event is active now, else None. Cached 30s."""
    t = time.time()
    if t - _event_cache["checked"] > 30:
        _event_cache["active"] = get_active_event()
        _event_cache["checked"] = t
    return _event_cache["active"]


def generate_frames(operator_email=None, source=None, operator_username="system"):
    """Live feed: reads, detects, and yields frames. Stops AUTOMATICALLY when the
    browser disconnects (no background thread -> no alarms after logout)."""
    
    # Optional: If you are using a CCTV camera, uncomment the next line and replace '0' below
    # cctv_url = "rtsp://admin:SecurePass2026@192.168.1.150:554/cam/realmonitor?channel=1&subtype=1"
    cctv_url = "rtsp://admin:YourPassword@192.168.1.150:554/Streaming/Channels/101"
    
    # Safest selection logic:
    if source == 'cctv':
        camera = cv2.VideoCapture(cctv_url)  # 1. Use CCTV if specifically requested
    elif source:
        camera = cv2.VideoCapture(source)    # 2. Use demo.mp4 if requested
    else:
        camera = cv2.VideoCapture(0)
    
    violence_detector.buffer.clear(); violence_detector.prob_hist.clear(); violence_detector._count = 0
    fail_count = 0
    DETECT_EVERY = 15  # Optimized person detection frequency
    WEAPON_EVERY = 10  # Optimized weapon detection frequency 
    frame_no = 0
    person_boxes, weapon_boxes = [], []
    person_count, track_ids, weapons = 0, [], []
    
    try:
        while True:
            success, frame = camera.read()
            if not success:
                if source:  # VIDEO FILE -> loop back to the start
                    camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    fail_count += 1
                    if fail_count > 5:
                        break
                    continue
                # CCTV/Network drop handling: wait a fraction of a second and try again
                time.sleep(0.1)
                continue
                
            fail_count = 0
            frame = cv2.resize(frame, (640, 480))

            is_violent, violence_prob = violence_detector.update(frame)

            frame_no += 1
            if frame_no % DETECT_EVERY == 0:
                person_boxes, person_count, track_ids = _detect_persons(frame)
            if frame_no % WEAPON_EVERY == 0:
                weapon_boxes, weapons = _detect_weapons(frame)
            
            img = _draw_boxes(frame.copy(), person_boxes + weapon_boxes)

            ev = current_event()
            tier, alert_type, message, conf = assessor.assess(
                violence_prob=violence_prob, weapons=weapons,
                person_count=person_count, track_ids=track_ids,
                current_hour=datetime.now().hour,
                event_active=ev is not None,
                event_expected_crowd=(ev[1] if ev else 0)
            )

            if tier != IGNORE:
                cv2.putText(img, message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, TIER_COLOR.get(tier, (0, 0, 255)), 2)
                            
                if _should_act(alert_type):
                    # Pass the logged-in operator's username to the database logger
                    new_id = log_alert(alert_type, conf, operator_username)
                    
                    if tier == ALARM:
                        trigger_audio_alarm()
                    
                    if operator_email and send_email_alert and (time.time() - _last_email["t"] > 60):
                        _last_email["t"] = time.time()  # max ONE email per minute
                        threading.Thread(target=send_email_alert,
                                         args=(operator_email, message, new_id),
                                         daemon=True).start()  # non-blocking

            cv2.putText(img, f"Violence: {violence_prob:.2f}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255) if is_violent else (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        camera.release()  # always release when the browser disconnects

# ================= SUDARSHAN'S ROUTES =================

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
        login_id = request.form['username'] 
        password = request.form['password']
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                if user['role'].lower() == role_type.lower():
                    session['username'] = user['username']
                    session['role'] = user['role']
                    session['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return redirect(url_for('dashboard'))
                else:
                    flash(f"Access Denied: This account does not have {role_type} privileges.", "error")
            else:
                flash("Invalid username/email or password.", "error")
                
    return render_template('login.html', role_type=role_type)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=?", (username,))
            if cursor.fetchone():
                flash("Username already exists.", "error")
                return redirect(url_for('signup'))
                
            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, 'Operator')", 
                (username, hashed_pw, email)
            )
            conn.commit()
            
        flash("Account created! Please log in to the Operator portal.", "success")
        return redirect(url_for('login', role_type='operator'))
        
    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    run_live = request.args.get('live', 'false') == 'true'
    
    login_time = session.get('login_time', '1970-01-01 00:00:00')
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC", (login_time,))
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
            
    video = request.args.get('video') or None
    return Response(generate_frames(operator_email, source=video, operator_username=session['username']),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_alerts')
def get_alerts():
    if 'username' not in session:
        return "Unauthorized", 401
        
    login_time = session.get('login_time', '1970-01-01 00:00:00')
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC", (login_time,))
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


@app.route('/alerts_history')
def alerts_history():
    if 'username' not in session:
        return redirect(url_for('index'))
        
    current_role = session.get('role', '').lower()
    current_username = session['username']
        
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if current_role == 'admin':
            cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
        else:
            cursor.execute("SELECT * FROM alerts WHERE operator_username=? ORDER BY timestamp DESC", (current_username,))
            
        all_alerts = [dict(row) for row in cursor.fetchall()]
        
    return render_template('alerts.html', username=current_username, role=session.get('role', ''), alerts=all_alerts)


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
        
        cursor.execute("SELECT id, username, email, role FROM users")
        active_users = cursor.fetchall()
        
        cursor.execute("SELECT original_user_id, username, email, role, deleted_at FROM deleted_users ORDER BY deleted_at DESC")
        archived_users = cursor.fetchall()
        
    return render_template('users.html', 
                           username=session['username'], 
                           role=current_role, 
                           users=active_users, 
                           deleted_users=archived_users)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))
        
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, email, role FROM users WHERE id=?", (user_id,))
        user_to_delete = cursor.fetchone()
        
        if user_to_delete:
            if user_to_delete[1] == session['username']:
                flash("You cannot delete your own active admin account.", "error")
            else:
                cursor.execute('''
                    INSERT INTO deleted_users (original_user_id, username, email, role, deleted_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_to_delete[0], user_to_delete[1], user_to_delete[2], user_to_delete[3], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
                cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
                conn.commit()
                flash("User successfully removed and archived.", "success")
        else:
            flash("User not found.", "error")
            
    return redirect(url_for('users'))


@app.route('/dismiss/<int:alert_id>/<token>')
def dismiss_alert(alert_id, token):
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


@app.route('/events')
def events():
    if 'username' not in session:
        return redirect(url_for('index'))
    if session.get('role', '').lower() != 'admin':
        flash("Access Denied: Administrator privileges required.", "error")
        return redirect(url_for('dashboard'))
        
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM events ORDER BY event_date DESC")
        active_events = cursor.fetchall()
        
        cursor.execute("SELECT * FROM deleted_events ORDER BY deleted_at DESC")
        archived_events = cursor.fetchall()
        
    return render_template('events.html', username=session['username'], role=session['role'], events=active_events, deleted_events=archived_events)


@app.route('/delete_event/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))
        
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, event_date, name, start_hour, end_hour, expected_crowd FROM events WHERE id=?", (event_id,))
        event_to_delete = cursor.fetchone()
        
        if event_to_delete:
            cursor.execute('''
                INSERT INTO deleted_events (original_event_id, event_date, name, start_hour, end_hour, expected_crowd, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (event_to_delete[0], event_to_delete[1], event_to_delete[2], event_to_delete[3], event_to_delete[4], event_to_delete[5], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
            conn.commit()
            flash("Event successfully removed and archived.", "success")
        else:
            flash("Event not found.", "error")
            
    return redirect(url_for('events'))


@app.route('/events/add', methods=['POST'])
def add_event_route():
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))
    add_event(request.form['event_date'], request.form['name'],
              request.form['start_hour'], request.form['end_hour'],
              request.form['expected_crowd'])
    flash("Event scheduled.", "success")
    return redirect(url_for('events'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/database_viewer')
def database_viewer():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    all_users = cursor.fetchall()

    cursor.execute("SELECT * FROM deleted_users")
    del_users = cursor.fetchall()

    cursor.execute("SELECT * FROM events")
    all_events = cursor.fetchall()

    cursor.execute("SELECT * FROM deleted_events")
    del_events = cursor.fetchall()

    cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC")
    all_alerts = cursor.fetchall()

    conn.close()

    return render_template('database_viewer.html', 
                           users=all_users, 
                           deleted_users=del_users,
                           events=all_events, 
                           deleted_events=del_events,
                           alerts=all_alerts)

if __name__ == '__main__':
    app.run(debug=True, port=5001, threaded=True)