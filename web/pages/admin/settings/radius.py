from flask import Blueprint, abort, jsonify, request

from core.admin.tables.settings.radius import add_radius_host, delete_radius_host, get_radius_hosts, update_radius_host
from core.config.defaults import DEFAULT_RADIUS_ACCT_PORT, DEFAULT_RADIUS_AUTH_PORT, DEFAULT_RADIUS_COA_PORT
from core.utils.language import get_translate
from web.pages.admin.settings.common import render_settings_page
from web.pages.admin.utils import login_required
from web.structures import ViewFieldType, ViewItem, ViewItemField


radius_bp = Blueprint('radius', __name__, url_prefix='/radius')
ITEM_ACTIONS = ['save', 'delete']
DEFAULT_ENABLED = True


def _build_host_item(data: dict) -> ViewItem:
    return ViewItem(
        name=data.get('name'),
        enabled=data.get('enabled'),
        fields=[
            ViewItemField(
                name='enabled',
                label='Enabled',
                type=ViewFieldType.CHECKBOX,
                value=data.get('enabled'),
            ),
            ViewItemField(
                name='name',
                label='Name',
                type=ViewFieldType.TEXT,
                value=data.get('name'),
            ),
            ViewItemField(
                name='address',
                label='Address',
                type=ViewFieldType.TEXT,
                value=data.get('address'),
            ),
            ViewItemField(
                label='Secret',
                type=ViewFieldType.PASSWORD,
                name='secret',
                value=data.get('secret'),
            ),
            ViewItemField(
                label='Auth port',
                type=ViewFieldType.TEXT,
                name='auth',
                value=data.get('authport'),
            ),
            ViewItemField(
                label='Acct port',
                type=ViewFieldType.TEXT,
                name='acct',
                value=data.get('acctport'),
            ),
            ViewItemField(
                label='CoA port',
                type=ViewFieldType.TEXT,
                name='coa',
                value=data.get('coaport'),
            ),
        ],
        actions=ITEM_ACTIONS,
    )


def _build_empty_host_item() -> ViewItem:
    return ViewItem(
        name='New Host',
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                name='enabled',
                label='Enabled',
                type=ViewFieldType.CHECKBOX,
                value=DEFAULT_ENABLED,
            ),
            ViewItemField(
                name='name',
                label='Name',
                type=ViewFieldType.TEXT,
            ),
            ViewItemField(
                name='address',
                label='Address',
                type=ViewFieldType.TEXT,
            ),
            ViewItemField(
                label='Secret',
                type=ViewFieldType.PASSWORD,
                name='secret',
            ),
            ViewItemField(
                label='Auth port',
                type=ViewFieldType.TEXT,
                name='auth',
                value=DEFAULT_RADIUS_AUTH_PORT,
            ),
            ViewItemField(
                label='Acct port',
                type=ViewFieldType.TEXT,
                name='acct',
                value=DEFAULT_RADIUS_ACCT_PORT,
            ),
            ViewItemField(
                label='CoA port',
                type=ViewFieldType.TEXT,
                name='coa',
                value=DEFAULT_RADIUS_COA_PORT,
            ),
        ],
        actions=ITEM_ACTIONS,
    )


@radius_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    return render_settings_page(
        'admin/settings/radius.html',
        source=get_radius_hosts(),
        item_builder=_build_host_item,
        empty_item=_build_empty_host_item(),
    )


@radius_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    host_id = req.get('id').strip()
    enabled = req.get('enabled')
    fields = req.get('fields')
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
        return jsonify({'success': False, 'error': {'description': error_message}})
    
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
        return jsonify({'success': False, 'error': {'description': error_message}})
