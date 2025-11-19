import secrets
from app.pages.auth import auth_bp
from app.pages.admin import admin_bp
from app.pages.error import error_bp

from flask import Blueprint, session


pages_bp = Blueprint('pages', __name__)

bluepints = [
    auth_bp,
    admin_bp,
    error_bp
]

for bp in bluepints:
    pages_bp.register_blueprint(bp)

@pages_bp.before_request
def ensure_session_id():
    if "_id" not in session:
        session["_id"] = secrets.token_hex(32)
