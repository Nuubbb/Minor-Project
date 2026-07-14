"""api"""

import sqlite3
from flask import Blueprint, request, jsonify, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash

from database import (
    DATABASE,
    mark_false_alarm,
    get_all_events,
    add_event,
    delete_user,
    delete_event,
    get_community_members,
    add_community_member,
    delete_community_member,
    get_device_location,
    update_device_location,
    log_alert,
    create_peer_report,
    get_pending_reports_for,
    get_peer_report,
    resolve_peer_report,
)
from auth import issue_token, token_required, admin_required
from detection import generate_frames
from config import SCREENSHOT_DIR

try:
    from email_alert import send_community_alert
except Exception:
    send_community_alert = None

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _row_to_alert(row):
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "alert_type": row["alert_type"],
        "confidence": row["confidence"],
        "is_false_alarm": bool(row["is_false_alarm"]),
        "operator_username": row["operator_username"],
    }


def _row_to_event(row):
    return {
        "id": row["id"],
        "event_date": row["event_date"],
        "name": row["name"],
        "start_hour": row["start_hour"],
        "end_hour": row["end_hour"],
        "expected_crowd": row["expected_crowd"],
    }


def _row_to_user(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
    }


def _row_to_community_member(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "lat": row["lat"],
        "lng": row["lng"],
    }


# ----------------- AUTH -----------------


@api_bp.route("/login/<role_type>", methods=["POST"])
def api_login(role_type):
    role_type = role_type.capitalize()
    if role_type not in ("Admin", "Operator", "Resident"):
        return jsonify({"error": "Invalid role"}), 400

    data = request.get_json(silent=True) or {}
    login_id = data.get("username")
    password = data.get("password")
    if not login_id or not password:
        return jsonify({"error": "username and password are required"}), 400

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id)
        )
        user = cursor.fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username/email or password."}), 401

    if user["role"].lower() != role_type.lower():
        return (
            jsonify(
                {
                    "error": f"Access Denied: This account does not have {role_type} privileges."
                }
            ),
            403,
        )

    token = issue_token(user)
    return jsonify(
        {
            "token": token,
            "username": user["username"],
            "role": user["role"],
            "email": user["email"],
        }
    )


@api_bp.route("/signup", methods=["POST"])
def api_signup():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            return jsonify({"error": "Username already exists."}), 409

        hashed_pw = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, 'Operator')",
            (username, hashed_pw, email),
        )
        conn.commit()

    return jsonify({"message": "Account created"}), 201


@api_bp.route("/me")
@token_required
def api_me():
    u = request.jwt_user
    return jsonify({"username": u["sub"], "role": u["role"], "email": u["email"]})


@api_bp.route("/logout", methods=["POST"])
def api_logout():
    # JWTs are stateless; the client simply discards the token. Route kept for symmetry.
    return jsonify({"message": "Logged out"})


# ----------------- ALERTS -----------------


@api_bp.route("/alerts")
@token_required
def api_alerts():
    u = request.jwt_user
    limit = request.args.get("limit", type=int)

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if u["role"].lower() == "admin":
            query = "SELECT * FROM alerts ORDER BY timestamp DESC"
            params = ()
        else:
            query = (
                "SELECT * FROM alerts WHERE operator_username=? ORDER BY timestamp DESC"
            )
            params = (u["sub"],)
        if limit:
            query += " LIMIT ?"
            params = params + (limit,)
        cursor.execute(query, params)
        alerts = cursor.fetchall()

    return jsonify({"alerts": [_row_to_alert(a) for a in alerts]})


@api_bp.route("/alerts/history")
@token_required
def api_alerts_history():
    return api_alerts()


@api_bp.route("/alerts/<int:alert_id>/false_alarm", methods=["POST"])
@token_required
def api_mark_false_alarm(alert_id):
    mark_false_alarm(alert_id)
    return jsonify({"message": "Alert marked as false alarm"})


# ----------------- LIVE VIDEO FEED -----------------
# NOTE: token is read from the ?token= query string here (not the Authorization header) because
# this endpoint is consumed by a WebView/<img> tag on the mobile client, which can't attach custom
# headers to the underlying multipart image request. This is an intentional, scoped exception to
# header-based auth -- see the plan doc for the security trade-off (token visible in server logs).
@api_bp.route("/video_feed")
@token_required
def api_video_feed():
    u = request.jwt_user
    operator_email = None
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT email FROM users WHERE username=?", (u["sub"],)
        ).fetchone()
        if row:
            operator_email = row["email"]

    video = request.args.get("video") or None
    return Response(
        generate_frames(operator_email, source=video, operator_username=u["sub"]),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ----------------- EVENTS (admin only) -----------------


@api_bp.route("/events")
@token_required
@admin_required
def api_events():
    events = get_all_events()
    return jsonify({"events": [_row_to_event(e) for e in events]})


@api_bp.route("/events", methods=["POST"])
@token_required
@admin_required
def api_add_event():
    data = request.get_json(silent=True) or {}
    required = ("event_date", "name", "start_hour", "end_hour", "expected_crowd")
    if not all(k in data for k in required):
        return jsonify({"error": f"Required fields: {', '.join(required)}"}), 400

    add_event(
        data["event_date"],
        data["name"],
        data["start_hour"],
        data["end_hour"],
        data["expected_crowd"],
    )
    return jsonify({"message": "Event scheduled."}), 201


@api_bp.route("/events/<int:event_id>", methods=["DELETE"])
@token_required
@admin_required
def api_delete_event(event_id):
    status, _ = delete_event(event_id)
    if status == "not_found":
        return jsonify({"error": "Event not found."}), 404
    return jsonify({"message": "Event successfully removed and archived."})


# ----------------- USERS (admin only) -----------------


@api_bp.route("/users")
@token_required
@admin_required
def api_users():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users")
        users = cursor.fetchall()
    return jsonify({"users": [_row_to_user(uu) for uu in users]})


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@token_required
@admin_required
def api_delete_user(user_id):
    status, _ = delete_user(user_id, request.jwt_user["sub"])
    if status == "not_found":
        return jsonify({"error": "User not found."}), 404
    if status == "self":
        return (
            jsonify({"error": "You cannot delete your own active admin account."}),
            400,
        )
    return jsonify({"message": "User successfully removed and archived."})


# ----------------- COMMUNITY (Resident accounts) -----------------


@api_bp.route("/community")
@token_required
def api_community():
    return jsonify(
        {"community": [_row_to_community_member(m) for m in get_community_members()]}
    )


@api_bp.route("/community", methods=["POST"])
@token_required
@admin_required
def api_add_community_member():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("email"):
        return jsonify({"error": "name and email are required"}), 400
    username, password = add_community_member(
        data["name"], data["email"], data.get("phone"), data.get("lat"), data.get("lng")
    )
    return (
        jsonify(
            {
                "message": "Resident account created.",
                "username": username,
                "password": password,
            }
        ),
        201,
    )


@api_bp.route("/community/<int:member_id>", methods=["DELETE"])
@token_required
@admin_required
def api_delete_community_member(member_id):
    status = delete_community_member(member_id)
    if status == "not_found":
        return jsonify({"error": "Community member not found."}), 404
    return jsonify({"message": "Community member removed."})


# ----------------- DEVICE LOCATION -----------------


@api_bp.route("/device_location")
@token_required
def api_device_location():
    return jsonify(get_device_location())


@api_bp.route("/device_location", methods=["PUT"])
@token_required
@admin_required
def api_update_device_location():
    data = request.get_json(silent=True) or {}
    label, lat, lng = data.get("label"), data.get("lat"), data.get("lng")
    if not label or lat is None or lng is None:
        return jsonify({"error": "label, lat, and lng are required"}), 400
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lng must be numbers"}), 400
    update_device_location(label, lat, lng)
    return jsonify(get_device_location())


# ----------------- MESSAGE PACKETS -----------------
# Real screenshot (when one was captured) + real recipients (Resident
# accounts) + a real, admin-set location. No dedicated packets table --
# assembled on the fly from `alerts` + screenshot files on disk.
# Human-reported alerts (alert_type='peer-reported', see /peer_reports below)
# have no camera screenshot, so screenshot_url is null for those rather than
# excluding them entirely -- they still need to flow through Take-a-Look /
# Notify-Community like any other alert.


def _row_to_packet(a, recipients, location):
    has_screenshot = (SCREENSHOT_DIR / f"alert_{a['id']}.jpg").exists()
    return {
        "id": a["id"],
        "alert_type": a["alert_type"],
        "confidence": a["confidence"],
        "timestamp": a["timestamp"],
        "operator_username": a["operator_username"],
        "is_false_alarm": bool(a["is_false_alarm"]),
        "screenshot_url": (
            f"/api/message_packets/{a['id']}/screenshot" if has_screenshot else None
        ),
        "location": location,
        "recipients": recipients,
    }


@api_bp.route("/message_packets")
@token_required
def api_message_packets():
    limit = request.args.get("limit", type=int) or 20

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        alerts = conn.execute(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()

    recipients = [_row_to_community_member(m) for m in get_community_members()]
    location = get_device_location()

    packets = [_row_to_packet(a, recipients, location) for a in alerts]

    return jsonify({"message_packets": packets})


@api_bp.route("/message_packets/<int:alert_id>/screenshot")
@token_required
def api_message_packet_screenshot(alert_id):
    path = SCREENSHOT_DIR / f"alert_{alert_id}.jpg"
    if not path.exists():
        return jsonify({"error": "No screenshot for this alert"}), 404
    return send_file(path, mimetype="image/jpeg")


@api_bp.route("/message_packets/<int:alert_id>/send", methods=["POST"])
@token_required
def api_send_message_packet(alert_id):
    if not send_community_alert:
        return jsonify({"error": "Email sending is not available on this server."}), 503

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        alert = conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()

    if not alert:
        return jsonify({"error": "Alert not found."}), 404

    screenshot_path = SCREENSHOT_DIR / f"alert_{alert_id}.jpg"
    screenshot_path = str(screenshot_path) if screenshot_path.exists() else None

    recipients = [_row_to_community_member(m) for m in get_community_members()]
    if not recipients:
        return jsonify({"error": "No community members to send to."}), 400

    sent, failed = send_community_alert(
        alert_id=alert["id"],
        alert_type=alert["alert_type"],
        message=alert["alert_type"].replace("-", " ").capitalize(),
        confidence=alert["confidence"],
        timestamp=alert["timestamp"],
        screenshot_path=screenshot_path,
        location=get_device_location(),
        recipients=recipients,
        reported_by=alert["operator_username"],
    )
    return jsonify(
        {
            "message": f"Sent to {sent} community member(s).",
            "sent": sent,
            "failed": failed,
        }
    )


# ----------------- PEER REPORTS (resident-to-resident suspicious activity) -----------------


def _row_to_peer_report(row):
    return {
        "id": row["id"],
        "reporter_user_id": row["reporter_user_id"],
        "reporter_username": row["reporter_username"],
        "owner_user_id": row["owner_user_id"],
        "message": row["message"],
        "status": row["status"],
        "timestamp": row["timestamp"],
    }


def _current_user_id():
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username=?", (request.jwt_user["sub"],)
        ).fetchone()
    return row[0] if row else None


@api_bp.route("/peer_reports", methods=["POST"])
@token_required
def api_create_peer_report():
    data = request.get_json(silent=True) or {}
    owner_user_id = data.get("owner_user_id")
    if not owner_user_id:
        return jsonify({"error": "owner_user_id is required"}), 400

    reporter_id = _current_user_id()
    if reporter_id is None:
        return jsonify({"error": "Could not resolve current user."}), 400
    if reporter_id == owner_user_id:
        return jsonify({"error": "You cannot report your own camera."}), 400

    report_id = create_peer_report(reporter_id, owner_user_id, data.get("message"))
    return jsonify({"message": "Report sent to the house owner.", "id": report_id}), 201


@api_bp.route("/peer_reports")
@token_required
def api_list_peer_reports():
    if request.args.get("for_me") != "true":
        return jsonify({"error": "Only ?for_me=true is supported."}), 400
    owner_id = _current_user_id()
    if owner_id is None:
        return jsonify({"error": "Could not resolve current user."}), 400
    reports = get_pending_reports_for(owner_id)
    return jsonify({"peer_reports": [_row_to_peer_report(r) for r in reports]})


@api_bp.route("/peer_reports/<int:report_id>/validate", methods=["POST"])
@token_required
def api_validate_peer_report(report_id):
    report = get_peer_report(report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404

    caller_id = _current_user_id()
    if caller_id != report["owner_user_id"]:
        return jsonify({"error": "Only the house owner can validate this report."}), 403

    data = request.get_json(silent=True) or {}
    confirmed = bool(data.get("confirmed"))

    status = resolve_peer_report(report_id, confirmed)
    if status == "not_found":
        return jsonify({"error": "Report already resolved."}), 409

    if confirmed:
        # Reuses the existing ML-alert pipeline instead of a parallel one --
        # this alert now shows up in Dashboard/History/Take-a-Look exactly
        # like a model-detected one, and "Notify Community" works unchanged.
        log_alert("peer-reported", 1.0, report["owner_username"])

    return jsonify({"message": "confirmed" if confirmed else "dismissed"})
