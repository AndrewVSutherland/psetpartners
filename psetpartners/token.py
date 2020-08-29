from .app import app
from itsdangerous import URLSafeTimedSerializer, URLSafeSerializer

def generate_token(obj, salt, key=None):
    if not key:
        key = app.config["SECRET_KEY"]
    return URLSafeSerializer(key).dumps(obj, salt=salt)

def read_token(token, salt, key=None):
    if not key:
        key = app.config["SECRET_KEY"]
    return URLSafeSerializer(key).loads(token, salt=salt)

# this does not work
def generate_timed_token(obj, salt, key=None):
    if not key:
        key = app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(key).dumps(obj, salt=salt)

def read_timed_token(token, salt, expiration=86400, key=None):
    if not key:
        key = app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(key).loads(token, salt=salt, max_age=expiration)
