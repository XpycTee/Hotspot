from flask import Blueprint, abort, jsonify, render_template, request

from core.admin.tables.settings.radius import add_radius_host, delete_radius_host, get_radius_hosts, update_radius_host
from core.config.defaults import DEFAULT_RADIUS_ACCT_PORT, DEFAULT_RADIUS_AUTH_PORT, DEFAULT_RADIUS_COA_PORT
from core.utils.language import get_translate
from web.pages.admin.utils import login_required


radius_bp = Blueprint('radius', __name__, url_prefix='/radius')


@radius_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    hosts = get_radius_hosts()

    template = render_template(
        'admin/settings/radius.html', 
        hosts=hosts
    )
    
    return template


@radius_bp.route('/get', methods=['GET'])
@login_required(group='full')
def get_hosts():
    hosts = get_radius_hosts()

    template = jsonify({'success': True, 'data': hosts})
    
    return template


@radius_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    hosts = req.get('hosts')
    for h in hosts:
        host_id = h.get('id').strip()
        enabled = h.get('enabled')
        fields = h.get('fields')
        address = fields.get('address').strip()

        update = {
            'enabled': enabled,
            'address': address,
            'name': fields.get('name').strip(),
            'secret': fields.get('secret', '').strip().encode(),
            'authport': fields.get('auth', DEFAULT_RADIUS_AUTH_PORT),
            'acctport': fields.get('acct', DEFAULT_RADIUS_ACCT_PORT),
            'coaport': fields.get('coa', DEFAULT_RADIUS_COA_PORT),
        }
        
        if host_id.startswith('new_'):
            response = add_radius_host(**update)
        else:
            response = update_radius_host(host_id, **update)

        status = response.get('status')
        if status != 'OK':
            error_message = response.get('error_message')
            return jsonify({'success': False, 'error_message': error_message})
    
    return jsonify({'success': True})


@radius_bp.route('/delete', methods=['POST'])
@login_required(group='full')
def delete():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    host = req.get('id')

    response = delete_radius_host(host)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    else:
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})
