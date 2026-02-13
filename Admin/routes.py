from flask import Flask, request, jsonify, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from Database.db import get_db_connection
from Utils.util import current_date_time
from Security.jwt import token_required, role_required, status_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/v1/add-new-account', methods=['POST'])
@token_required
@status_required("active")
@role_required("admin")
def add_new_user():
    data = request.get_json(silent=True)

    if not data or not all(k in data for k in ("roll", "section", "name")):
        return jsonify({"error": "Missing required fields: name, roll, or section"}), 400

    name = data.get("name")
    roll = data.get("roll")
    section = data.get("section")
    
    hash_password = generate_password_hash(roll)

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM users WHERE roll=%s", (roll,))
        if cur.fetchone():
            return jsonify({"error": "User with this roll number already exists"}), 409

        cur.execute(
            "INSERT INTO users(name, roll, password, section, created_at, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, roll, hash_password, section, current_date_time(), "active")
        )
        db.commit()
        return jsonify({"msg": "Account added sucessfully"}), 201
    except Exception as e:
        db.rollback()
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()



@admin_bp.route('/v1/admin-delete-user/<int:id>', methods=["DELETE"])
@token_required
@status_required("active")
@role_required("admin")
def admin_delete_user(id):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            DELETE FROM users
            WHERE id = %s
        """, (id,))
        db.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"msg": "User Delete Sucessful"}), 200

    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cur.close()
        db.close()



@admin_bp.route("/v1/storage", methods=["GET"])
@token_required
@status_required("active")
@role_required("admin")
def get_db_storage():
    db = None
    cur = None
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        query = """
            SELECT 
                table_name,
                table_rows AS total_rows,
                ROUND(data_length / 1024 / 1024, 2) AS data_mb,
                ROUND(index_length / 1024 / 1024, 2) AS index_mb,
                ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_mb
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY total_mb DESC
        """
        
        cur.execute(query)
        tables = cur.fetchall()

        # Calculate Grand Totals for the header
        total_db_size = sum(table['total_mb'] for table in tables)
        total_data_size = sum(table['data_mb'] for table in tables)
        total_index_size = sum(table['index_mb'] for table in tables)

        return jsonify({
            "status": "success",
            "summary": {
                "database_name": "defaultdb",
                "total_combined_mb": round(total_db_size, 2),
                "total_pure_data_mb": round(total_data_size, 2),
                "total_index_usage_mb": round(total_index_size, 2)
            },
            "table_details": tables
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if cur:
            cur.close()
        if db:
            db.close()

@admin_bp.route('/v1/all-users/', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def all_account():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, roll, section, created_at, status FROM users WHERE role=%s ORDER BY id DESC",("user",))
        accounts = cur.fetchall()

        return jsonify({"accounts": accounts})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()

@admin_bp.route('/v1/user-profile-details/<int:id>')
@token_required
@status_required("active")
@role_required("admin")
def user_profile_details(id):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, roll, section, created_at, status, max_size, size_per_file FROM users WHERE id=%s AND role=%s",(id, "user"))
        accounts = cur.fetchall()

        cur.execute("SELECT id, file_name, file_size, subject, exp_number, is_public, uploaded_at FROM stored_files WHERE user_id=%s ORDER BY id DESC",(id,))
        files = cur.fetchall()

        return jsonify({"accounts": accounts, "files": files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


@admin_bp.route('/v1/admin-delete-file/<int:id>')
@token_required
@status_required("active")
@role_required("admin")
def admin_delete_file(id):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""
            DELETE FROM stored_files
            WHERE id = %s
        """, (id,))
        db.commit()
        return jsonify({"msg": "Delete Sucessful"}), 200

    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()

@admin_bp.route('/v1/admin-public-file/<int:id>')
@token_required
@status_required("active")
@role_required("admin")
def admin_public_file(id):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT is_public FROM stored_files WHERE id=%s",(id,))
        res = cur.fetchone()

        if res["is_public"] == "yes":
            return jsonify({"msg": "file is already public"}), 200

        cur.execute("UPDATE stored_files SET is_public=%s WHERE id=%s", ("yes",id))
        db.commit()
        return jsonify({"msg": "Public sucessful Sucessful"}), 200

    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()

@admin_bp.route('/v1/admin-private-file/<int:id>')
@token_required
@status_required("active")
@role_required("admin")
def admin_private_file(id):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT is_public FROM stored_files WHERE id=%s",(id,))
        res = cur.fetchone()

        if res["is_public"] == "no":
            return jsonify({"msg": "file is already private"}), 200

        cur.execute("UPDATE stored_files SET is_public=%s WHERE id=%s", ("no",id))
        db.commit()
        return jsonify({"msg": "File Private Sucessful"}), 200

    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()



@admin_bp.route('/v1/dashboard', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def dashboard():
    db = None
    cur = None
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        
        # Added WHERE role = 'user' to exclude admins from the counts
        query = (
            "SELECT "
            "COUNT(*) AS total_user, "
            "SUM(status = 'active') AS active_count, "
            "SUM(status = 'deactive') AS deactive_count, "
            "SUM(status = 'block') AS blocked_count, "
            "SUM(status = 'requested') AS pending_count "
            "FROM users "
            "WHERE role = 'user'"
        )
        
        cur.execute(query)
        res = cur.fetchone()

        # Check if res is None (empty table) and handle NULLs from SUM()
        if not res:
            return jsonify({
                "total_user": 0,
                "active_count": 0,
                "deactive_count": 0,
                "blocked_count": 0,
                "pending_count": 0
            }), 200

        return jsonify({
            "total_user": res["total_user"] or 0,
            "active_count": int(res["active_count"] or 0),
            "deactive_count": int(res["deactive_count"] or 0),
            "blocked_count": int(res["blocked_count"] or 0),
            "pending_count": int(res["pending_count"] or 0)
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        if cur: cur.close()
        if db: db.close()


@admin_bp.route('/v1/admin-reset-user-password/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def reset_user_password(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        hash_password = generate_password_hash(roll)

        cur.execute("UPDATE users SET password=%s WHERE roll=%s", (hash_password,roll))
        db.commit()
        return jsonify({"msg": "Password Reset sucessful"}), 200

    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()



@admin_bp.route('/v1/total-files-count', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def total_file_counts():
    db = None
    cur = None
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        

        query = (
            "SELECT "
            "COUNT(*) AS total_files, "
            "SUM(is_public = 'yes') AS public_files, "
            "SUM(is_public = 'no') AS private_files "
            "FROM stored_files "
            "WHERE status = 'active'"
        )
        
        cur.execute(query)
        res = cur.fetchone()

        # Check if res is None (empty table) and handle NULLs from SUM()
        if not res:
            return jsonify({
                "total_files": 0,
                "public_files": 0,
                "private_files": 0
            }), 200

        return jsonify({
            "total_files": res["total_files"] or 0,
            "public_files": int(res["public_files"] or 0),
            "private_files": int(res["private_files"] or 0)
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
    finally:
        if cur: cur.close()
        if db: db.close()

@admin_bp.route('/v1/admin-all-files', methods=['GET'] )
@token_required
@status_required("active")
@role_required("admin")
def admin_all_files():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:

        cur.execute("SELECT id, user_id, file_name, file_size, subject, exp_number, is_public, uploaded_at FROM stored_files WHERE status=%s ORDER BY id DESC",("active",))
        files = cur.fetchall()

        return jsonify({"files": files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()

@admin_bp.route('/v1/admin-all-public-files', methods=['GET'] )
@token_required
@status_required("active")
@role_required("admin")
def admin_all_public_files():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:

        cur.execute("SELECT id, user_id, file_name, file_size, subject, exp_number, uploaded_at FROM stored_files WHERE is_public=%s ORDER BY id DESC",("yes",))
        files = cur.fetchall()

        return jsonify({"files": files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()

@admin_bp.route('/v1/admin-all-private-files', methods=['GET'] )
@token_required
@status_required("active")
@role_required("admin")
def admin_all_private_files():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:

        cur.execute("SELECT id, user_id, file_name, file_size, subject, exp_number, uploaded_at FROM stored_files WHERE is_public=%s ORDER BY id DESC",("no",))
        files = cur.fetchall()

        return jsonify({"files": files})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()







# ========================= requested or pending section =====================================
@admin_bp.route('/v1/requested-accounts/', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def requested_account():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, roll, section, created_at, status FROM users WHERE status=%s AND role=%s",("requested", "user"))
        accounts = cur.fetchall()

        return jsonify({"accounts": accounts})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()



@admin_bp.route('/v1/accept-account-request/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def accept_account_request(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400
        
        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("active", roll))
        db.commit()
        return jsonify({"msg": "Active Sucessfully"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


# ========================= block section =====================================
@admin_bp.route('/v1/block-accounts/', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def blocked_accounts():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT name, roll, section, created_at, status FROM users WHERE status=%s",("block",))
        accounts = cur.fetchall()

        return jsonify({"accounts": accounts})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


@admin_bp.route('/v1/mark-unblock-account/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def mark_unblock_account(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400
        
        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("active", roll))
        db.commit()
        return jsonify({"msg": "Unblock Sucessfully"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()




@admin_bp.route('/v1/mark-block-account/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def mark_block_account(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400

        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("block", roll))
        db.commit()
        return jsonify({"msg": "Block Sucessfully"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()




# ========================= deactvat section =====================================
@admin_bp.route('/v1/deactive-accounts/', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def deactive_accounts():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, roll, section, created_at, status FROM users WHERE status=%s",("deactive",))
        accounts = cur.fetchall()

        return jsonify({"accounts": accounts})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


@admin_bp.route('/v1/mark-active-account/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def mark_actives_account(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400
        
        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("active", roll))
        db.commit()
        return jsonify({"msg": "Active Sucessfull"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()



# =========================  deactive section =====================================
@admin_bp.route('/v1/active-accounts/', methods=['GET'])
@token_required
@status_required("active")
@role_required("admin")
def active_accounts():

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, roll, section, created_at, status FROM users WHERE status=%s AND role=%s",("active", "user"))
        accounts = cur.fetchall()

        return jsonify({"accounts": accounts})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()


@admin_bp.route('/v1/mark-deactive-account/<string:roll>')
@token_required
@status_required("active")
@role_required("admin")
def mark_deactives_account(roll):

    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("SELECT status FROM users WHERE roll=%s",(roll,))
        status = cur.fetchone()

        if not status:
            return jsonify({"msg":"User not found"}), 400

        cur.execute("UPDATE users SET status=%s WHERE roll=%s",("deactive", roll))
        db.commit()
        return jsonify({"msg": "Deactive Sucessfull"})
    
    except Exception as e:
        print(f"Error = {str(e)}")
        return jsonify({"error": "Internal server error"})
    finally:
        cur.close()
        db.close()