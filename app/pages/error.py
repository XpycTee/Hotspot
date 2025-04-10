from flask import Blueprint, render_template, current_app
from werkzeug.exceptions import HTTPException

error_bp = Blueprint('errors', __name__)


@error_bp.app_errorhandler(HTTPException)
def error_handler(err):
    return render_template(
        'auth/error.html',
        code=err.code,
        title=current_app.config['LANGUAGE_CONTENT']['errors']['http'][str(err.code)]['title'],
        description=current_app.config['LANGUAGE_CONTENT']['errors']['http'][str(err.code)]['description']), err.code
