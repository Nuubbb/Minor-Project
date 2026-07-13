import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, render_template_string, send_file
from werkzeug.security import generate_password_hash, check_password_hash

from config import SECRET_KEY, SCREENSHOT_DIR
from database import (init_db, mark_false_alarm, DATABASE,
                      init_events, add_event, delete_user, delete_event,
                      get_device_location)
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
    """Dummy/dev-only page to eyeball the message-packet prototype (screenshot +
    placeholder location + recipients) before the real screenshot/map UI is ready."""
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
    app.run(host='0.0.0.0', debug=True, port=5001, threaded=True)
