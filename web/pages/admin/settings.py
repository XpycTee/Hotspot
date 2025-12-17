from flask import Blueprint, abort, jsonify, render_template, request, session

from core.admin.tables.settings import get_settings, radius_delete_host, update_settings
from core.utils.language import get_translate
from web.pages.admin.utils import login_required


settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('', methods=['POST', 'GET'])
@login_required
def index():
    error = session.pop('error', None)
    return render_template('admin/settings.html', error=error)


@settings_bp.route('/<table_name>/save', methods=['POST'])
@login_required
def save_data(table_name):
    data = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))
        
    response = update_settings(table_name, data)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    else:
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})


@settings_bp.route('/radius/delete', methods=['POST'])
@login_required
def delete_host():
    data = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))
    
    response = radius_delete_host(data)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    else:
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})


@settings_bp.route('/<table_name>', methods=['GET'])
@login_required
def get_table(table_name):
    response = get_settings(table_name)
    if not response:
        abort(404)
        
    return jsonify({
        'data': response
    })