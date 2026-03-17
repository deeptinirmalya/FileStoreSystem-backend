from flask import Flask, request, jsonify, Blueprint, send_file
from Database.db import get_db_connection
from Utils.util import current_date, current_date_time, current_time, check_total_size, check_file_size
from Security.jwt import token_required, role_required, status_required
from Database.db import get_db_connection
from werkzeug.security import check_password_hash, generate_password_hash
import os
import base64
import json
import io

user_bp = Blueprint('user', __name__)



@user_bp.route('/v1/new-account', methods=['POST'])
def add_new_user():
    data = request.get_json(silent=True)

    if not data or not all(k in data for k in ("roll", "password", "section", "name")):
        return jsonify({"error": "Missing required fields: name, roll, password, or section"}), 400

    name = data.get("name")
    roll = data.get("roll")
    password = data.get("password")
    section = data.get("section")
    
    hash_password = generate_password_hash(password)

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM users WHERE roll=%s", (roll,))
        if cur.fetchone():
            return jsonify({"error": "User with this roll number already exists"}), 409

        cur.execute(
            "INSERT INTO users(name, roll, password, section, created_at, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, roll, hash_password, section, current_date_time(), "requested")
        )
        db.commit()
        return jsonify({"msg": "Account created. Please ask admin for activation."}), 201
    except Exception as e:
        db.rollback()
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()




@user_bp.route('/v1/request-for-activate-account', methods=['POST'])
def request_for_activate():
    data = request.get_json(silent=True)

    if not data or "roll" not in data:
        return jsonify({"error": "Missing roll number"}), 400

    roll = data.get("roll")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400

        if status["status"] == "active":
            return jsonify({"msg":"The given user is a active user"}), 400
        
        if status["status"] == "block":
            return jsonify({"msg":"The given user is a blocked contact to the admin"}), 400
        
        if status["status"] == "requested":
            return jsonify({"msg":"Alredy request for activate wait for admin Action"}), 400
        
        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("requested", roll))
        db.commit()
        return jsonify({"msg": "Request Send Sucessfully"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


@user_bp.route('/v1/profile', methods=['GET'])
@token_required
@status_required("active")
@role_required('user')
def user_profile():
    user_id = request.user_id

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT name, roll, section, role, created_at, size_per_file, max_size, status FROM users WHERE id=%s",(user_id,))
        details = cur.fetchone()

        cur.execute("SELECT SUM(file_size) AS total_size FROM stored_files WHERE user_id=%s",(user_id,))
        res = cur.fetchone()
        total_size = res["total_size"] if res["total_size"] is not None else 0

        return jsonify({"name":details["name"],
                        "roll":details["roll"],
                        "section":details["section"],
                        "role":details["role"],
                        "created_at":details["created_at"],
                        "size_per_file":details["size_per_file"],
                        "max_size":details["max_size"],
                        "status":details["status"],
                        "space_occupied": total_size
                        }), 200
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()


@user_bp.route('/v1/dashboard', methods=['GET'])
@token_required
@status_required("active")
@role_required('user')
def dashboard():
    user_id = request.user_id

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, file_name, file_size, subject, exp_number, uploaded_at FROM stored_files WHERE user_id=%s AND status=%s ORDER BY id DESC",(user_id, "active"))
        files = cur.fetchall()

        return jsonify({"files":files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()

@user_bp.route('/v1/dashboard/public-files', methods=['GET'])
def dashboard_public_files():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, file_name, file_size, subject, exp_number, uploaded_at FROM stored_files WHERE is_public=%s ORDER BY id DESC",("yes",))
        files = cur.fetchall()

        return jsonify({"files":files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()


@user_bp.route('/v1/upload-file', methods=['POST'])
@token_required
@status_required("active")
@role_required('user')
def upload_file_json():
    user_id = request.user_id
    data = request.get_json()

    if not data or 'file_data' not in data:
        return jsonify({"error": "No data provided"}), 400

    try:
        full_name = data.get('file_name', 'unknown.bin')
        subject = data.get('subject')
        exp_number = data.get('exp_number')

        file_ext = os.path.splitext(full_name)[1].lower()
        encoded_str = data['file_data'].split(',')[1]
        file_binary_data = base64.b64decode(encoded_str)
        file_size = len(file_binary_data)

        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT COALESCE(SUM(file_size), 0) AS total_size_occupied FROM stored_files WHERE user_id=%s", (user_id,))
        res = cur.fetchone()

        cur.execute("SELECT max_size, size_per_file FROM users WHERE id=%s",(user_id,))
        details = cur.fetchone()

        if not check_file_size(file_binary_data, int(details["size_per_file"])):
            return jsonify({"msg":f"File size should be less then {int(details["size_per_file"])/1024}Kb"}), 413

        if not check_total_size(file_binary_data, res["total_size_occupied"], int(details["max_size"])):
            return jsonify({"msg":"You reach the max storage with this file"}), 413


        cur.execute("INSERT INTO stored_files (user_id, file_name, file_ext, file_size, file_data, subject, exp_number, uploaded_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (user_id, full_name, file_ext, file_size, file_binary_data, subject, exp_number, current_date_time()))
        db.commit()

        return jsonify({
            "success": True,
            "msg":"Upload sucessful"}), 200

    except Exception as e:
        db.rollback()
        print(f"{str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()



@user_bp.route('/v1/view-file/<int:file_id>')
def view_file(file_id):
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            SELECT file_name, file_ext, file_data
            FROM stored_files
            WHERE id = %s AND status=%s
        """, (file_id, "active"))
        file = cur.fetchone()

        try:
            content = file["file_data"].decode("utf-8")
        except UnicodeDecodeError:
            content = "[❌ Binary file — cannot display as text]"

        return jsonify({
            "filename": file["file_name"],
            "extension": file["file_ext"],
            "content": content
        })

    except Exception as e:
        print(f"{str(e)}")
        return jsonify({"error":"Internal server error"}), 500
    
    finally:
        cur.close()
        db.close()


@user_bp.route('/v1/delete-file/<int:file_id>', methods=['DELETE'])
@token_required
@status_required("active")
@role_required('user')
def delete_file(file_id):
    user_id = request.user_id
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        cur.execute("""
            DELETE FROM stored_files
            WHERE id = %s AND user_id=%s
        """, (file_id, user_id))
        db.commit()
        return jsonify({"msg": "Delete Sucessful"}), 200

    except Exception as e:
        db.rollback()
        print(f"{str(e)}")
        return jsonify({"error":"Internal Server error"}), 500
    finally:
        cur.close()
        db.close()



@user_bp.route('/v1/download/<int:file_id>')
def download_file(file_id):
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT file_name, file_data FROM stored_files WHERE id = %s",(file_id,))
        result = cur.fetchone()

        if not result:
            return jsonify({"error":"File not found"}), 400

        file_name = result["file_name"]
        file_data = result["file_data"]

        return send_file(
            io.BytesIO(file_data),
            download_name=file_name,
            as_attachment=True
        )

    except Exception as e:
        print("error:", str(e))
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        db.close()
        cur.close()
    

# === NOTICE PAGE ====

FILE_PATH = "message.json"


if not os.path.exists(FILE_PATH):
    with open(FILE_PATH, "w") as f:
        json.dump({"message": ""}, f)
        
@user_bp.route("/v1/view-notice", methods=["GET"])
def view_notice():
    with open(FILE_PATH, "r") as f:
        data = json.load(f)
    return jsonify(data)
