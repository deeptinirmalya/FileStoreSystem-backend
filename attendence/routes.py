from flask import Flask, request, jsonify, Blueprint
from Database.db import get_db_connection
from Utils.util import current_date, current_date_time, current_time, check_total_size, check_file_size
from Security.jwt import token_required, role_required, status_required
from Database.db import get_db_connection
from werkzeug.security import check_password_hash, generate_password_hash
import os
import requests
import math
from dotenv import load_dotenv

load_dotenv()

attendence_bp = Blueprint('attendence', __name__)


def calculate_attendance_metrics(attendance_list):
    total_attended = 0
    total_conducted = 0
    
    for day in attendance_list:
        if "Total" in day:
            att, cond = map(int, day["Total"].split('/'))
            total_attended += att
            total_conducted += cond
        
    if total_conducted == 0:
        return 0.0, "No classes conducted yet.", 0, "neutral"
        
    current_pct = (total_attended / total_conducted) * 100
    
    if current_pct < 80.0:
        needed = math.ceil((0.80 * total_conducted - total_attended) / 0.20)
        needed = max(0, needed) 
        message = f"{needed} consecutive classes to reach the 80% Attendance."
        action_value = needed
        status = "shortage"
    else:
        can_bunk = math.floor((total_attended / 0.80) - total_conducted)
        can_bunk = max(0, can_bunk)
        message = f"You can safely bunk {can_bunk} classes."
        action_value = can_bunk
        status = "safe"

    return round(current_pct, 2), message, action_value, status

@attendence_bp.route("/v1/get_attendance", methods=["GET"])
@token_required
@status_required("active")
@role_required("user")
def get_attendance():
    user_id = request.user_id

    roll_number = request.args.get("roll_number")

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    
    try:
        cur.execute("SELECT status FROM users WHERE id=%s", (user_id,))
        details = cur.fetchone()
        
        if not details:
            return jsonify({"detail": "User record not found."}), 404
            
        if details["status"] != "active":
            return jsonify({"detail": "account is not active contact to the admin"}), 503
        
        roll_number = roll_number.upper()

        url = os.getenv("ERP_URL")
        erp_url = f"{url}{roll_number}"

        try:
            response = requests.get(erp_url, timeout=10.0)
            if response.status_code != 200:
                return jsonify({"detail": "Failed to fetch data from ERP server."}), response.status_code
                
            erp_data = response.json()
        except requests.exceptions.RequestException as exc:
            print(exc)
            return jsonify({"detail": "internal server unreachable"}), 503

        attendance_list = erp_data.get("dataAttendance", [])
        if not attendance_list:
            return jsonify({"detail": "No attendance logs discovered for this roll number."}), 404
            
        percentage, message, action_value, status = calculate_attendance_metrics(attendance_list)
        
        return jsonify({
            "roll_number": roll_number,
            "percentage": percentage,
            "message": message,
            "action_value": action_value,
            "status": status,
            "mail_sent": True
        }), 200

    finally:
        # Properly indented inside the function block to ensure cleanup
        cur.close()
        db.close()