from flask import Blueprint, request, jsonify
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash
from extension import limiter
from Security.jwt import generate_token, token_required, status_required, role_required
from Database.db import get_db_connection
from Utils.util import send_pushbullet_msg, current_date_time

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/v1/login", methods=["POST"])
@limiter.limit(
    "5 per minute",
    key_func=lambda: (
        (request.get_json(silent=True) or {}).get("roll", "").lower()
        or get_remote_address()
    )
)
def login():
    data = request.get_json(silent=True)

    if not data or "roll" not in data or "password" not in data:
        return jsonify({"error": "Missing roll number or password"}), 400

    roll = data.get("roll")
    password = data.get("password")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, password, role, status FROM users WHERE roll=%s", (roll,))
        user = cur.fetchone()

        if not user:
            return jsonify({"msg": "user not found "}), 401
    
        if not check_password_hash(user["password"], password):
            return jsonify({"message": "Invalid credentials"}), 401

        cur.execute("UPDATE users SET last_login=%s WHERE roll=%s", (current_date_time(), roll))
        db.commit()

        token = generate_token(
            user_id=user["id"],
            role=user["role"],
            status=user["status"]
            )
        
        return jsonify({
            "msg": "login success",
            "access_token": token,  # The frontend will read this
            "role": user["role"],
            "status": user["status"]
        }), 200

    finally:
        cur.close()
        db.close()






@auth_bp.route("/v1/change-password", methods=["POST"])
@token_required
@status_required("active")
@role_required("user")
def change_password():
    user_id = request.user_id
    data = request.get_json(silent=True)

    if not data or "old_password" not in data or "new_password" not in data:
        return jsonify({"error": "Missing old password or new password"}), 400

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    try:
        cur.execute("SELECT password, status FROM users WHERE id=%s",(user_id,))
        details = cur.fetchone()

        if details["status"] != "active":
            return jsonify({"msg": "Password Change Did not allow"}), 400
        
        if not check_password_hash(details["password"], old_password):
            return jsonify({"msg": "Old password din not match"}), 400
        
        hash_password = generate_password_hash(new_password)

        cur.execute("UPDATE users SET password=%s WHERE id=%s",(hash_password, user_id))
        db.commit()

        return jsonify({"msg":"Password update sucessful"}), 200
    
    except Exception as e:
        db.rollback()
        print(f"{str(e)}")
        return jsonify({"msg": "Internal Server Error"}), 500
    finally:
        db.close()