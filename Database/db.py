from mysql.connector import pooling
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

# Absolute path to backend/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SSL_CA_RELATIVE = os.getenv("SSL_CA")
SSL_CA = os.path.join(BASE_DIR, SSL_CA_RELATIVE)

# Hard fail early (good)
if not os.path.exists(SSL_CA):
    raise FileNotFoundError(f"SSL CA file not found: {SSL_CA}")

db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT")),
    "ssl_ca": SSL_CA
}

connection_pool = pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=10,
    **db_config
)

def get_db_connection():
    return connection_pool.get_connection()



# def get_db_connection():
#     try:
#         return mysql.connector.connect(
#             host=os.getenv("DB_HOST"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             database=os.getenv("DB_DATABASE")
#         )
#     except mysql.connector.Error as e:
#         print(f"❌ Database error: {e}")
#         return None


# try:
#     conn = get_db_connection()
#     if conn.is_connected():
#         print("✅ Success: Connection established. FOR CLOUD DB  WITH POOLING")
#         conn.close()
# except Exception as e:
#     print(f"❌ Failed: {e}")