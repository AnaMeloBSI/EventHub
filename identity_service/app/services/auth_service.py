import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from app.extensions import db
from app.models.user import User

VALID_ROLES = {"ADMIN", "ORGANIZER", "PARTICIPANT"}

def generate_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.user_id,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=current_app.config["JWT_EXPIRATION_SECONDS"])).timestamp()),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

def verify_access_token(token: str):
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

def require_role(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header.", "details": {}}}), 401

            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = verify_access_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": {"code": "TOKEN_EXPIRED", "message": "Access token has expired.", "details": {}}}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": {"code": "INVALID_TOKEN", "message": "Invalid access token.", "details": {}}}), 401

            if allowed_roles and payload.get("role") not in allowed_roles:
                return jsonify({"error": {"code": "FORBIDDEN", "message": "Insufficient permissions for this role.", "details": {}}}), 403

            request.current_user = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def seed_default_admin():
    admin_email = "admin@eventhub.edu.br"
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name="Administrador Geral", email=admin_email, role="ADMIN")
        admin.set_password("Admin@123")
        db.session.add(admin)
        db.session.commit()