from flask import Blueprint, abort, jsonify, render_template, request

from core.admin.tables.settings.radius import add_radius_host, delete_radius_host, get_radius_hosts, update_radius_host, update_radius_hosts
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


@radius_bp.route('/add', methods=['POST'])
@login_required(group='full')
def add_host():
    data: dict = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    # Basic validation: required fields
    required_fields = ['address', 'name', 'secret']
    for field in required_fields:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            return jsonify({'success': False, 'error_message': f'Missing or empty field: {field}'}), 400

    # Validate ports (optional) and convert to ints
    ports = {}
    for p in ('authport', 'acctport', 'coaport'):
        v = data.get(p)
        if v in (None, ''):
            ports[p] = None
            continue
        try:
            pv = int(v)
            if pv < 1 or pv > 65535:
                return jsonify({'success': False, 'error_message': f'Invalid port value for {p}'}), 400
            ports[p] = pv
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error_message': f'Invalid port value for {p}'}), 400

    new_host_data = {
        'address': data.get('address').strip(),
        'name': data.get('name').strip(),
        'secret': data.get('secret', '').strip().encode(),
        'authport': ports.get('authport', DEFAULT_RADIUS_AUTH_PORT),
        'acctport': ports.get('acctport', DEFAULT_RADIUS_ACCT_PORT),
        'coaport': ports.get('coaport', DEFAULT_RADIUS_COA_PORT),
    }

    response = add_radius_host(**new_host_data)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    else:
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})


@radius_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update_host():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    update = {}
    hosts = req.get('hosts')
    for h in hosts:
        host = h.get('id')
        enabled = h.get('enabled')
        fields = h.get('fields')
        update[host] = {
            'enabled': enabled,
            'address': fields.get('address').strip(),
            'name': fields.get('name').strip(),
            'secret': fields.get('secret', '').strip().encode(),
            'authport': fields.get('auth', DEFAULT_RADIUS_AUTH_PORT),
            'acctport': fields.get('acct', DEFAULT_RADIUS_ACCT_PORT),
            'coaport': fields.get('coa', DEFAULT_RADIUS_COA_PORT),
        }

    response = update_radius_hosts(update)

    status = response.get('status')
    if status != 'OK':
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})
    
    return jsonify({'success': True})


@radius_bp.route('/delete', methods=['POST'])
@login_required(group='full')
def delete_host():
    data = request.json

    if not data:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    # Basic validation: required fields

    host = data.get('host')
    if host is None or (isinstance(host, str) and not host.strip()):
        return jsonify({'success': False, 'error_message': f'Missing or empty field: host'}), 400

    response = delete_radius_host(host)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    else:
        error_message = response.get('error_message')
        return jsonify({'success': False, 'error_message': error_message})
