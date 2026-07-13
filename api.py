import sqlite3
from flask import Blueprint, request, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash

from database import (DATABASE, mark_false_alarm, get_all_events, add_event,
                       delete_user, delete_event)
from auth import issue_token, token_required, admin_required
from detection import generate_frames

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
    return {"id": row["id"], "username": row["username"], "email": row["email"], "role": row["role"]}


# ----------------- AUTH -----------------

@api_bp.route("/login/<role_type>", methods=["POST"])
def api_login(role_type):
    role_type = role_type.capitalize()
    if role_type not in ("Admin", "Operator"):
        return jsonify({"error": "Invalid role"}), 400

    data = request.get_json(silent=True) or {}
    login_id = data.get("username")
    password = data.get("password")
    if not login_id or not password:
        return jsonify({"error": "username and password are required"}), 400

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id))
        user = cursor.fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username/email or password."}), 401

    if user["role"].lower() != role_type.lower():
        return jsonify({"error": f"Access Denied: This account does not have {role_type} privileges."}), 403

    token = issue_token(user)
    return jsonify({"token": token, "username": user["username"], "role": user["role"], "email": user["email"]})


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
            (username, hashed_pw, email)
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
            query = "SELECT * FROM alerts WHERE operator_username=? ORDER BY timestamp DESC"
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
        row = conn.execute("SELECT email FROM users WHERE username=?", (u["sub"],)).fetchone()
        if row:
            operator_email = row["email"]

    video = request.args.get("video") or None
    return Response(generate_frames(operator_email, source=video, operator_username=u["sub"]),
                     mimetype="multipart/x-mixed-replace; boundary=frame")


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

    add_event(data["event_date"], data["name"], data["start_hour"], data["end_hour"], data["expected_crowd"])
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
        return jsonify({"error": "You cannot delete your own active admin account."}), 400
    return jsonify({"message": "User successfully removed and archived."})
