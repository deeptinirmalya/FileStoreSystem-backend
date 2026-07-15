from flask import Flask, request, jsonify, Blueprint
from Database.db import get_db_connection
from Utils.util import current_date, current_date_time, current_time
from Database.db import get_db_connection
from urllib.parse import urlparse
from dotenv import load_dotenv
from extension import limiter, get_client_ip

import os
import json
import re

load_dotenv()

stp_bp = Blueprint('stp', __name__)


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def validate_creator_request(data):
    errors = {}

    # Name
    name = str(data.get("name", "")).strip()
    if not name:
        errors["name"] = "Name is required."
    elif len(name) < 2:
        errors["name"] = "Name must be at least 2 characters."
    elif len(name) > 100:
        errors["name"] = "Name cannot exceed 100 characters."


    whatsapp_number = data.get("whatsapp_number")
    if whatsapp_number:
        whatsapp_number = str(whatsapp_number).strip()

        if len(whatsapp_number) > 10:
            errors["whatsapp_number"] = "WhatsApp number cannot exceed 10 characters."
        if len(whatsapp_number) < 10:
            errors["whatsapp_number"] = "WhatsApp number cannot must be 10 characters."
        elif not PHONE_REGEX.fullmatch(whatsapp_number):
            errors["whatsapp_number"] = "Invalid WhatsApp number."

    # Email
    email = str(data.get("email", "")).strip().lower()
    if not email:
        errors["email"] = "Email is required."
    elif len(email) > 255:
        errors["email"] = "Email cannot exceed 255 characters."
    elif not EMAIL_REGEX.fullmatch(email):
        errors["email"] = "Invalid email address."

    # Platform Link
    platform_link = str(data.get("platform_link", "")).strip()
    if not platform_link:
        errors["platform_link"] = "Platform link is required."
    elif len(platform_link) > 512:
        errors["platform_link"] = "Platform link cannot exceed 512 characters."
    elif not is_valid_url(platform_link):
        errors["platform_link"] = "Invalid URL."

    # Niche
    nich = str(data.get("nich", "")).strip()
    if not nich:
        errors["nich"] = "Niche is required."
    elif len(nich) < 2:
        errors["nich"] = "Niche must be at least 2 characters."
    elif nich not in ["Food & Cafes", "Lifestyle & Fashion", "Education", "Tech", "Dance & Music", "Blogging", "Travel & Entertainment", "Photography & Videography", "Other"]:
        errors["nich"] = "Niche must be from the drop menu "
    elif len(nich) > 100:
        errors["nich"] = "Niche cannot exceed 100 characters."

    return errors


@stp_bp.route('/v1/creator_entry', methods=['POST'])
@limiter.limit("100 per day",
    on_breach=lambda rl: (
        jsonify({
            "success": False,
            "message": "You can only submit this form 1 times per hour."
        }),
        429
    ))
def creator_entry():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400
    
    # print(data)

    errors = validate_creator_request(data)
    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400

    ip = get_client_ip()
    user_agent = request.headers.get("User-Agent", "")

    # Cleaned values
    name = data["name"].strip()
    whatsapp_number = data.get("whatsapp_number")
    whatsapp_number = str(whatsapp_number).strip() if whatsapp_number else None

    email = data["email"].strip().lower()
    platform_link = data["platform_link"].strip()
    nich = data["nich"].strip()

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    try:


        cur.execute(
            "SELECT id FROM creator_entry WHERE email=%s",(email,))
        if cur.fetchone():
            return jsonify({
                "success": False,
                "error": "This email has already submitted."
            }), 409
        
        cur.execute(
            "SELECT id FROM creator_entry WHERE whatsapp_number=%s",(whatsapp_number,))
        if cur.fetchone():
            return jsonify({
                "success": False,
                "error": "This whatsApp number is already exist has already submitted."
            }), 409
            
        cur.execute(
            "SELECT id FROM creator_entry WHERE ip_address=%s",(ip,))
        if cur.fetchone():
            return jsonify({
                "success": False,
                "error": "you have already submitted a request."
            }), 409

        cur.execute("""
            INSERT INTO creator_entry
            (
                name,
                whatsapp_number,
                email,
                platform_link,
                niche,
                ip_address,
                user_agent,
                created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            name,
            whatsapp_number,
            email,
            platform_link,
            nich,
            ip,
            user_agent,
            current_date_time()
        ))

        db.commit()

        return jsonify({
            "success": True,
            "message": "Request submitted successfully."
        }), 201

    except Exception as e:
        db.rollback()
        # print(e)

        return jsonify({
            "success": False,
            "error": "Internal server error."
        }), 500

    finally:
        cur.close()
        db.close()


# ================================= b or busenn ======================

ALLOWED_INDUSTRIES = {
    "Hospitality & Food",
    "Retail & Boutiques",
    "Local Startups",
    "Wellness & Gyms",
    "Events & Entertainment"
}

ALLOWED_OPERATION_TYPES = {"Physical", "Digital", "Hybrid"}

ALLOWED_REVENUE_RANGES = {
    "0-5000",
    "5001-10000",
    "10001-30000",
    "30001-50000",
    "50001-100000",
    "100001+"  
}

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
WHATSAPP_REGEX = r'^[6-9]\d{9}$'


def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False


def validate_payload(data):
    errors = []

    if not isinstance(data, dict):
        return ["Invalid payload structure: Must be a JSON object."]

    required_string_fields = {
        "businessLocation": 150,  
        "companyName": 100,
        "contactName": 100,
        "email": 254,
        "whatsapp": 10,
        "socialLink": 550,       
        "industry": 100,
        "operationType": 50,
        "revenue": 50
    }


    for field, max_len in required_string_fields.items():
        val = data.get(field)
        if not val or not isinstance(val, str) or not val.strip():
            errors.append(f"Field '{field}' is required and must be a non-empty string.")
        elif len(val) > max_len:
            errors.append(f"Field '{field}' exceeds max length of {max_len} characters.")


    email = data.get("email", "")
    if email and not re.match(EMAIL_REGEX, email):
        errors.append("Invalid email address format.")

    whatsapp = data.get("whatsapp", "")
    if whatsapp and not re.match(WHATSAPP_REGEX, str(whatsapp)):
        errors.append("Invalid WhatsApp number. Must be a 10-digit number.")

    social_link = data.get("socialLink", "")
    if social_link and not validate_url(social_link):
        errors.append("Invalid URL format for 'socialLink'. Must start with http:// or https://")

    if data.get("industry") not in ALLOWED_INDUSTRIES:
        errors.append("Invalid industry value.")

    if data.get("operationType") not in ALLOWED_OPERATION_TYPES:
        errors.append("Invalid operationType value.")

    if data.get("revenue") not in ALLOWED_REVENUE_RANGES:
        errors.append("Invalid revenue range value.")

    goals = data.get("goals")
    if goals is not None:
        if not isinstance(goals, dict):
            errors.append("Field 'goals' must be an object.")
        else:
            goal_keys = ["driveWalkIns", "appDownloads", "sellTickets", "brandAwareness", "platformTraffic"]
            for key in goal_keys:
                if key in goals and not isinstance(goals[key], bool):
                    errors.append(f"Goal property '{key}' must be a boolean.")

    return errors


@stp_bp.route("/v1/partners_entry", methods=["POST"])
@limiter.limit("100 per day",
    on_breach=lambda rl: (
        jsonify({
            "success": False,
            "message": "You can only submit this form 1 times per hour."
        }),
        429
    ))
def partners_entry():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"success": False, "message": "Invalid JSON payload"}), 400


    validation_errors = validate_payload(data)
    if validation_errors:
        # print("\nError data validation:", validation_errors)
        return jsonify({"success": False, "errors": validation_errors}), 422

    goals = data.get("goals", {})
    ip = get_client_ip()
    user_agent = request.headers.get("User-Agent", "")

    sql_query = """
        INSERT INTO partners_entry (
            partners_location, company_name, contact_name, email, whatsapp,
            social_link, industry, operation_type,
            goal_drive_walk_ins, goal_app_downloads, goal_sell_tickets,
            goal_brand_awareness, goal_platform_traffic, revenue, 
            ip_address, user_agent, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data["businessLocation"].strip(),
        data["companyName"].strip(),
        data["contactName"].strip(),
        data["email"].strip().lower(),
        data["whatsapp"].strip(),
        data["socialLink"].strip(),
        data["industry"],
        data["operationType"],
        1 if goals.get("driveWalkIns", False) else 0,
        1 if goals.get("appDownloads", False) else 0,
        1 if goals.get("sellTickets", False) else 0,
        1 if goals.get("brandAwareness", False) else 0,
        1 if goals.get("platformTraffic", False) else 0,
        data["revenue"],
        ip,
        user_agent,
        current_date_time()
    )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

        cursor.execute(
            "SELECT id FROM partners_entry WHERE email=%s",(data["email"].strip().lower(),))
        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "This email has already submitted."
            }), 409
        
        cursor.execute(
            "SELECT id FROM partners_entry WHERE whatsapp=%s",(data["whatsapp"].strip(),))
        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "This whatsApp number is already exist has already submitted."
            }), 409
        
        cursor.execute(
            "SELECT id FROM partners_entry WHERE ip_address=%s",(ip,))
        if cursor.fetchone():
            return jsonify({
                "success": False,
                "error": "you have already submitted a request."
            }), 409

        cursor.execute(sql_query, values)
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Partner lead saved successfully!"
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        # print(f"\nServer error: {str(e)}")
        return jsonify({"success": False, "errors": "Internal Server Error"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
