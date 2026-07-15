from extension import limiter
from flask import Flask, request, jsonify
from flask_cors import CORS
from Database.db import get_db_connection


app = Flask(__name__)


CORS(
    app,
    origins=["https://giet.netlify.app", "https://at-logs.netlify.app", "https://vibelist.in", "https://stp-validator.netlify.app"],
    supports_credentials=True
)

# CORS(
#     app, 
#     origins=["http://127.0.0.1:5501", "http://localhost:5501", "http://127.0.0.1:5173", "http://localhost:5173"], 
#     supports_credentials=True
# )

limiter.init_app(app)

from Auth.routes import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

from Admin.routes import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

from User.routes import user_bp
app.register_blueprint(user_bp, url_prefix='/user')

from attendence.routes import attendence_bp
app.register_blueprint(attendence_bp, url_prefix='/attendence')

from other.routes import stp_bp
app.register_blueprint(stp_bp, url_prefix='/stp')

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