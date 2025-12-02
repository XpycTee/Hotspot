import uuid
from web.pages.hotspot import hotspot_bp
from web.pages.admin import admin_bp
from web.pages.error import error_bp

from flask import Blueprint, session


pages_bp = Blueprint('pages', __name__)

bluepints = [
    hotspot_bp,
    admin_bp,
    error_bp
]

for bp in bluepints:
    pages_bp.register_blueprint(bp)

@pages_bp.before_request
def ensure_session_id():
    if "_id" not in session:
        session["_id"] = str(uuid.uuid4())
