from flask import Blueprint, render_template, request, jsonify
from werkzeug.exceptions import HTTPException

from core.utils.language import get_translate

error_bp = Blueprint('errors', __name__)


@error_bp.app_errorhandler(HTTPException)
def error_handler(err):
    # Check if the request expects a JSON response
    if request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
        response = {
            'success': False,
            'status_code': err.code,
            'error': {
                'name': err.name,
                'description': err.description
            }
        }
        return jsonify(response), err.code
    else:
        # Default to HTML response
        return render_template(
            'error.html',
            code=err.code,
            name=get_translate(f'errors.http."{str(err.code)}".name', err.name),
            description=get_translate(f'errors.http."{str(err.code)}".description', err.description)
        ), err.code
