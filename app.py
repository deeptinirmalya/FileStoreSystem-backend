from extension import limiter
from flask import Flask, request, jsonify
from flask_cors import CORS
from Database.db import get_db_connection

app = Flask(__name__)
CORS(app, supports_credentials=True)

limiter.init_app(app)

from Auth.routes import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

from Admin.routes import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

from User.routes import user_bp
app.register_blueprint(user_bp, url_prefix='/user')

@app.route('/', methods=['GET'])
def health_check():
    db = None
    try:
        db = get_db_connection()
        # Using buffered=True prevents the "Unread result" error
        cur = db.cursor(buffered=True) 
        cur.execute("SELECT 1")
        cur.fetchall() # Ensure we consume the result
        cur.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
    finally:
        if db:
            db.close()







#-------------------------- END POINT SECTION END ---------------------------------------------

if __name__ == "__main__":
    app.run()