from flask import Blueprint, render_template, current_app
from werkzeug.exceptions import HTTPException

from extensions import get_translate

error_bp = Blueprint('errors', __name__)


@error_bp.app_errorhandler(HTTPException)
def error_handler(err):
    return render_template(
        'error.html',
        code=err.code,
        title=get_translate(f'errors.http."{str(err.code)}".title'),
        description=get_translate(f'errors.http."{str(err.code)}".description')), err.code
