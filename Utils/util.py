from dotenv import load_dotenv
from pushbullet import Pushbullet
from datetime import datetime
from datetime import datetime
import secrets
import pytz
import os


load_dotenv()

IST = pytz.timezone("Asia/Kolkata")

def current_date_time():
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M")

def current_date():
    return datetime.now(IST).strftime("%Y-%m-%d")
    

def current_time():
    return datetime.now(IST).strftime("%H:%M")

def generate_txn_id():
    return secrets.token_urlsafe(32)




# max_size=1048576 # 1MB in Bytes
# in tha above I can pass the allow byte value in the from the db and store tha Byte value in the db like for 1MB = 1048576 Byts, 70 kb = 71680 Bytes
# max_size = 71680  # 70Kb in Bytes 70*1024

def check_file_size(file_binary_data, allowed_file_size):
    file_size = len(file_binary_data)

    if file_size  <= allowed_file_size:
        return True
    else:
        return False


def check_total_size(file_binary_data, occupied_size, max_size):

    file_size = len(file_binary_data)

    if (file_size + occupied_size) <= max_size:
        return True
    else:
        return False
    

def send_pushbullet_msg(title, body):
    access_token = os.getenv("PUSHBULLET_AUTH_KEY")
    pb = Pushbullet(access_token)

    try:
        pb.push_note(title, body)
        return True
    except Exception as e:
        print(f"Error occurred: {e}")
        return False
