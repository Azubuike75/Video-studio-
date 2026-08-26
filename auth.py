import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_PATH = os.path.join(BASE_DIR, "data", "auth.json")
SECRET_PATH = os.path.join(BASE_DIR, "data", "secret.key")


def is_configured():
    return os.path.exists(AUTH_PATH)


def set_credentials(username, password):
    os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
    with open(AUTH_PATH, "w") as f:
        json.dump({"username": username, "password_hash": generate_password_hash(password)}, f)


def verify(username, password):
    if not is_configured():
        return False
    with open(AUTH_PATH) as f:
        data = json.load(f)
    return username == data["username"] and check_password_hash(data["password_hash"], password)


def get_username():
    if not is_configured():
        return None
    with open(AUTH_PATH) as f:
        return json.load(f)["username"]


def get_or_create_secret_key():
    os.makedirs(os.path.dirname(SECRET_PATH), exist_ok=True)
    if os.path.exists(SECRET_PATH):
        with open(SECRET_PATH) as f:
            return f.read().strip()
    key = os.urandom(32).hex()
    with open(SECRET_PATH, "w") as f:
        f.write(key)
    return key
