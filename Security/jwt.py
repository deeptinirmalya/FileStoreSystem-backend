import jwt
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
import os

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret")
JWT_ALGO = "HS256"
JWT_EXP_HOURS = 2

def generate_token(user_id, role, status):
    now = datetime.now(timezone.utc)
    payload = {
        "jti": str(uuid.uuid4()),
        "user_id": user_id,
        "role": role,
        "status": status,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXP_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = None
        
        # CHANGED: Look for the Authorization header instead of cookies
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1] # Extract the actual token

        if not token:
            return jsonify({"error": "Token is missing. Please log in."}), 401
            
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            # Store data in request object for downstream use
            request.user_id = payload["user_id"]
            request.role = payload["role"]
            request.status = payload["status"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # request.role is set by token_required
            current_role = getattr(request, 'role', None)
            if current_role not in allowed_roles:
                return jsonify({"error": f"Forbidden: {allowed_roles} access required"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

def status_required(*allowed_status):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # request.status is set by token_required
            current_status = getattr(request, 'status', None)
            if current_status not in allowed_status:
                return jsonify({"error": f"Forbidden: Account status '{allowed_status}' required"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

def get_client_ip(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        x_forwarded = request.headers.get('X-Forwarded-For')
        if x_forwarded:
            ip = x_forwarded.split(',')[0].strip()
        else:
            ip = request.remote_addr
        request.client_ip = ip
        return f(*args, **kwargs)
    return decorated_function