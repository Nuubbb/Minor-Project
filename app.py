import sqlite3
import random
from email_alert import send_verification_code
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import dns.resolver
from config import SECRET_KEY, SCREENSHOT_DIR
from database import (init_db, mark_false_alarm, DATABASE,
                      init_events, add_event, delete_user, delete_event,
                      get_device_location, update_device_location)
from detection import generate_frames
from api import api_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY
init_db()
init_events()
app.register_blueprint(api_bp)

# ----------------- INPUT SOURCE -----------------
USE_WEBCAM = True
VIDEO_PATH = "fight.mp4"

DISMISS_SECRET = "kec_surveillance_2026"   # MUST match email_alert.py

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
                user_status = user['status'] if user['status'] else 'approved'
                if user_status == 'pending':
                    flash("Your account is pending admin approval.", "warning")
                    return render_template('login.html', role_type=role_type)
                if user_status == 'rejected':
                    flash("Your registration request was rejected.", "error")
                    return render_template('login.html', role_type=role_type)
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

            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                flash("Email already registered.", "error")
                return redirect(url_for('signup'))
            # Check email domain exists
            try:
                domain = email.split('@')[1]
                dns.resolver.resolve(domain, 'MX')
            except Exception:
                flash("Invalid email domain. Please use a real email address.", "error")
                return redirect(url_for('signup'))
            code = str(random.randint(100000, 999999))
            hashed_pw = generate_password_hash(password)

            if not send_verification_code(email, code):
                flash("Could not send verification email. Please check your email address.", "error")
                return redirect(url_for('signup'))

            cursor.execute(
                "INSERT INTO email_verification (email, code, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (email, code, username, hashed_pw, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()

flash("If this email exists, you'll receive a verification code shortly.", "info")        return redirect(url_for('verify_email', email=email))

    return render_template('signup.html')


@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    email = request.args.get('email') or request.form.get('email', '')

    if request.method == 'POST':
        code = request.form['code']

        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM email_verification WHERE email=? AND code=? AND used=0 ORDER BY id DESC LIMIT 1",
                (email, code)
            )
            record = cursor.fetchone()

            if not record:
                flash("Invalid verification code.", "error")
                return render_template('verify_email.html', email=email)

            # Check if code is expired (10 minutes)
            created = datetime.strptime(record['created_at'], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - created).total_seconds() > 600:
                flash("Verification code expired. Please sign up again.", "error")
                return redirect(url_for('signup'))

            # Mark code as used
            cursor.execute("UPDATE email_verification SET used=1 WHERE id=?", (record['id'],))

            # Create the actual user account
            cursor.execute(
                "INSERT INTO users (username, password, email, role, status) VALUES (?, ?, ?, 'Operator', 'pending')",
                (record['username'], record['password_hash'], record['email'])
            )
            conn.commit()

        flash("Email verified! Your account is pending admin approval.", "success")
        return redirect(url_for('index'))

    return render_template('verify_email.html', email=email)
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

        # Threat type counts for charts
        cursor.execute("""
            SELECT alert_type, COUNT(*) as cnt,
                   SUM(CASE WHEN is_false_alarm = 0 THEN 1 ELSE 0 END) as active_cnt
            FROM alerts
            GROUP BY alert_type
        """)
        threat_stats = [dict(row) for row in cursor.fetchall()]

        # Alerts per day for line chart (last 7 days)
        cursor.execute("""
            SELECT DATE(timestamp) as day, COUNT(*) as cnt
            FROM alerts
            GROUP BY DATE(timestamp)
            ORDER BY day DESC
            LIMIT 7
        """)
        daily_stats = [dict(row) for row in cursor.fetchall()]
        daily_stats.reverse()

    return render_template('dashboard.html', username=session['username'],
                          role=session['role'], alerts=alerts, run_live=run_live,
                          threat_stats=threat_stats, daily_stats=daily_stats)


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
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    {% for alert in alerts %}
    <tr>
        <td style="color:#94a3b8; font-size:0.75rem; white-space:nowrap;">
            {{ alert.timestamp.split()[1] if alert.timestamp else '' }}
        </td>
        <td>
            {% set atype = alert.alert_type|lower %}
            <span style="display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:6px; font-weight:600; font-size:0.75rem; text-transform:capitalize;
                  {% if 'violen' in atype %}background:rgba(220,38,38,0.1); color:#dc2626;
                  {% elif 'weapon' in atype or 'gun' in atype or 'knife' in atype %}background:rgba(245,158,11,0.1); color:#d97706;
                  {% elif 'crowd' in atype %}background:rgba(14,165,233,0.1); color:#0284c7;
                  {% elif 'intrusion' in atype %}background:rgba(124,58,237,0.1); color:#7c3aed;
                  {% else %}background:#f1f5f9; color:#475569;{% endif %}">
                <i class="fas {% if 'violen' in atype %}fa-hand-fist{% elif 'weapon' in atype or 'gun' in atype or 'knife' in atype %}fa-crosshairs{% elif 'crowd' in atype %}fa-people-group{% elif 'intrusion' in atype %}fa-person-walking{% else %}fa-triangle-exclamation{% endif %}"></i>
                {{ alert.alert_type.replace('-', ' ') }}
            </span>
        </td>
        <td>
            {% set conf = (alert.confidence * 100)|int %}
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:0.78rem; font-weight:600; min-width:32px;">{{ conf }}%</span>
                <div style="flex:1; height:4px; background:#e2e8f0; border-radius:2px; overflow:hidden;">
                    <div style="height:100%; border-radius:2px; width:{{ conf }}%;
                        {% if conf >= 80 %}background:#dc2626;{% elif conf >= 50 %}background:#f59e0b;{% else %}background:#16a34a;{% endif %}
                        transition:width 0.8s ease;"></div>
                </div>
            </div>
        </td>
        <td>
            {% if alert.is_false_alarm %}
                <span style="color:#94a3b8; font-weight:600; font-size:0.78rem;"><i class="fas fa-check"></i> Dismissed</span>
            {% else %}
                <span style="color:#dc2626; font-weight:700; font-size:0.78rem; display:flex; align-items:center; gap:4px;">
                    <i class="fas fa-circle" style="font-size:0.4rem;"></i> Active
                </span>
            {% endif %}
        </td>
        <td>
            {% if not alert.is_false_alarm %}
            <form action="{{ url_for('flag_false_alarm', alert_id=alert.id) }}" method="POST" style="margin:0;">
                <button type="submit" style="padding:5px 12px; border-radius:6px; border:1px solid #e2e8f0; background:#f8fafc; color:#475569; font-size:0.72rem; font-weight:600; cursor:pointer;">Dismiss</button>
            </form>
            {% endif %}
        </td>
    </tr>
    {% else %}
    <tr>
        <td colspan="5">
            <div style="text-align:center; padding:50px 20px; color:#94a3b8;">
                <i class="fas fa-shield-check" style="font-size:2.5rem; opacity:0.3; margin-bottom:12px; display:block;"></i>
                <p>No security events detected</p>
            </div>
        </td>
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

        cursor.execute("SELECT id, username, email, role, status FROM users WHERE status='approved' OR status IS NULL")
        active_users = cursor.fetchall()

        cursor.execute("SELECT id, username, email, role FROM users WHERE status='pending'")
        pending_users = cursor.fetchall()

        cursor.execute("SELECT original_user_id, username, email, role, deleted_at FROM deleted_users ORDER BY deleted_at DESC")
        archived_users = cursor.fetchall()

    return render_template('users.html',
                           username=session['username'],
                           role=current_role,
                           users=active_users,
                           pending_users=pending_users,
                           deleted_users=archived_users)


@app.route('/delete_user/<int:user_id>', methods=['POST'], endpoint='delete_user')
def delete_user_route(user_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))

    status, _ = delete_user(user_id, session['username'])
    if status == "not_found":
        flash("User not found.", "error")
    elif status == "self":
        flash("You cannot delete your own active admin account.", "error")
    else:
        flash("User successfully removed and archived.", "success")

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


@app.route('/delete_event/<int:event_id>', methods=['POST'], endpoint='delete_event')
def delete_event_route(event_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))

    status, _ = delete_event(event_id)
    if status == "not_found":
        flash("Event not found.", "error")
    else:
        flash("Event successfully removed and archived.", "success")

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


@app.route('/message_packets_view')
def message_packets_view():
    if 'username' not in session:
        return redirect(url_for('index'))

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        alerts = conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 20").fetchall()
        recipients = [dict(u) for u in conn.execute(
            "SELECT username, email FROM users WHERE email IS NOT NULL AND email != ''"
        ).fetchall()]

    packets = []
    for a in alerts:
        if not (SCREENSHOT_DIR / f"alert_{a['id']}.jpg").exists():
            continue
        packets.append({**dict(a), "recipients": recipients})

    return render_template('message_packets.html', username=session['username'],
                            role=session['role'], packets=packets, location=get_device_location())


@app.route('/screenshots/<int:alert_id>')
def screenshot_view(alert_id):
    if 'username' not in session:
        return "Unauthorized", 401
    path = SCREENSHOT_DIR / f"alert_{alert_id}.jpg"
    if not path.exists():
        return "Not found", 404
    return send_file(path, mimetype='image/jpeg')


@app.route('/update_location', methods=['POST'])
def update_location():
    if 'username' not in session:
        return "Unauthorized", 401
    data = request.get_json(silent=True) or {}
    lat = data.get('lat')
    lng = data.get('lng')
    if lat is None or lng is None:
        return "Missing coordinates", 400
    update_device_location("Camera — Live GPS", float(lat), float(lng))
    return "OK", 200


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

@app.route('/approve_user/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE users SET status='approved' WHERE id=?", (user_id,))
        conn.commit()
    flash("User approved.", "success")
    return redirect(url_for('users'))


@app.route('/reject_user/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if 'username' not in session or session.get('role', '').lower() != 'admin':
        return redirect(url_for('index'))
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE users SET status='rejected' WHERE id=?", (user_id,))
        conn.commit()
    flash("User rejected.", "success")
    return redirect(url_for('users'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001, threaded=True)