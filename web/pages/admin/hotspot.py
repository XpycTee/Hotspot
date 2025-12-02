from datetime import datetime
from flask import Blueprint, abort, jsonify, request

from core.hotspot.user.blacklist import add_to_blacklist_by_mac
from core.hotspot.user.expiration import reset_expiration
from core.utils.language import get_translate
from web.pages.admin.utils import login_required


hotspot_bp = Blueprint('hotspot', __name__, url_prefix='/hotspot')


@hotspot_bp.route('/deauth', methods=['POST'])
@login_required
def deauth():
    data = request.json
    if not data or 'mac' not in data:
        abort(400, description=get_translate('errors.admin.tables.mac_is_missing'))

    mac_address = data.get('mac')
    reset_expiration(mac_address)

    return jsonify({'success': True})


@hotspot_bp.route('/block', methods=['POST'])
@login_required
def block():
    data = request.json
    if not data or 'mac' not in data:
        abort(400, description=get_translate('errors.admin.tables.mac_is_missing'))

    mac_address = data.get('mac')

    response = add_to_blacklist_by_mac(mac_address)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    
    if status == 'NOT_FOUND':
        error_message = response.get('error_message')
        abort(404, description=error_message)

    if status == 'ALREDY_BLOCKED':
        error_message = response.get('error_message')
        abort(400, description=error_message)
    
    abort(500, description="Unknown status")
