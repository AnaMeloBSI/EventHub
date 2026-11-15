from functools import wraps
import jwt
from flask import request, jsonify, current_app, g


def error_response(status_code, code, message, details=None):
    return jsonify({
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }), status_code


def verify_access_token(token):
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.decode(token, secret, algorithms=["HS256"])


def require_role(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return error_response(401, "MISSING_TOKEN", "Authorization Bearer token is required.")

            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = verify_access_token(token)
            except jwt.ExpiredSignatureError:
                return error_response(401, "TOKEN_EXPIRED", "Access token has expired.")
            except jwt.InvalidTokenError:
                return error_response(401, "INVALID_TOKEN", "Invalid access token.")

            user_id = payload.get("sub")
            role = payload.get("role")
            if not user_id or not role:
                return error_response(401, "INVALID_TOKEN_CLAIMS", "Token missing required claims.")

            if allowed_roles and role not in allowed_roles:
                return error_response(403, "FORBIDDEN", "Insufficient permissions for this resource.")

            g.current_user = {"user_id": user_id, "role": role}
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_internal_service(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Internal-Token", "")
        if not token or token != current_app.config["INTERNAL_SERVICE_TOKEN"]:
            return error_response(401, "UNAUTHORIZED_SERVICE", "Invalid or missing internal service token.")
        return fn(*args, **kwargs)
    return wrapper
