import uuid
from flask import Blueprint, session

from web.api.callcheck import callcheck_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')

bluepints = [
    callcheck_bp,
]

for bp in bluepints:
    api_bp.register_blueprint(bp)

@api_bp.before_request
def ensure_session_id():
    if "_id" not in session:
        session["_id"] = str(uuid.uuid4())
