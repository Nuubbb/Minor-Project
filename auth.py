import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify

from config import SECRET_KEY, JWT_ALGO, JWT_EXP_HOURS


def issue_token(user_row):
    """user_row must support ['username'] / ['role'] / ['email'] access (sqlite3.Row or dict)."""
    payload = {
        "sub": user_row["username"],
        "role": user_row["role"],
        "email": user_row["email"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGO)


def decode_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO])


def token_required(f):
    """Reads Authorization: Bearer <token>, OR ?token=<token> query param (needed for
    the MJPEG <img>/WebView route where custom headers aren't practical)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        if not token:
            token = request.args.get("token")
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        request.jwt_user = payload   # {"sub": username, "role": role, "email": email}
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Must be stacked INSIDE token_required (token_required closer to the route decorator
    list bottom) so request.jwt_user already exists."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.jwt_user.get("role", "").lower() != "admin":
            return jsonify({"error": "Admin privileges required"}), 403
        return f(*args, **kwargs)
    return wrapper
