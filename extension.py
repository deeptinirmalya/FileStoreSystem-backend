from flask import request, jsonify
from flask_limiter import Limiter
import os
from dotenv import load_dotenv

load_dotenv()


def get_client_ip():
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")

    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()

    return request.remote_addr


limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=os.getenv("REDIS_URL"),
    default_limits=["200 per day", "50 per hour"]
)