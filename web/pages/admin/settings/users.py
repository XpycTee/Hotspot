from flask import Blueprint, abort, jsonify, request, session

from core.admin.repository import create_user, delete_user, update_user
from core.admin.security.access import is_valid_group
from core.admin.tables.settings.users import get_users
from core.utils.language import get_translate
from web.pages.admin.settings.common import render_settings_page
from web.pages.admin.utils import login_required
from web.structures import ViewFieldType, ViewItem, ViewItemField


users_bp = Blueprint('users', __name__, url_prefix='/users')
ITEM_ACTIONS = ['save', 'delete']
DEFAULT_ENABLED = True


def _group_state(group: str | None) -> dict[str, bool]:
    return {
        'read': group == 'read',
        'write': group == 'write',
        'full': group == 'full',
    }


def _build_user_item(data: dict) -> ViewItem:
    return ViewItem(
        name=data.get('username'),
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                label='Group',
                type=ViewFieldType.SELECT,
                name='group',
                required=True,
                value=_group_state(data.get('group')),
            ),
            ViewItemField(
                label='Password',
                type=ViewFieldType.PASSWORD,
                name='password',
                required=False,
            ),
            ViewItemField(
                label='Confirm Password',
                type=ViewFieldType.PASSWORD_CONFIRM,
                name='password_confirm',
                required=False,
            ),
        ],
        actions=ITEM_ACTIONS,
    )


def _build_empty_user_item() -> ViewItem:
    return ViewItem(
        name='New User',
        enabled=DEFAULT_ENABLED,
        fields=[
            ViewItemField(
                label='Username',
                type=ViewFieldType.USERNAME,
                name='username',
                required=True,
            ),
            ViewItemField(
                label='Group',
                type=ViewFieldType.SELECT,
                name='group',
                required=True,
                value={'read': True, 'write': False, 'full': False},
            ),
            ViewItemField(
                label='Password',
                type=ViewFieldType.PASSWORD,
                name='password',
                required=False,
            ),
            ViewItemField(
                label='Confirm Password',
                type=ViewFieldType.PASSWORD_CONFIRM,
                name='password_confirm',
                required=False,
            ),
        ],
        actions=ITEM_ACTIONS,
    )


@users_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    return render_settings_page(
        'admin/settings/users.html',
        source=get_users(),
        item_builder=_build_user_item,
        empty_item=_build_empty_user_item(),
    )


@users_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    username = req.get('id')
    active_username = session.get('username')
    password = req['fields'].get('password', None)
    password_confirm = req['fields'].get('password_confirm', None)

    if username == active_username:
        return jsonify({'success': False, 'error': {'description': "You can't update your self"}})
    
    if password != password_confirm:
        return jsonify({'success': False, 'error': {'description': 'Passwords do not match'}})

    group = req['fields'].get('group', None)
    if not is_valid_group(group):
        return jsonify({'success': False, 'error': {'description': 'Bad group'}})

    if username.startswith('new_'):
        username = req['fields'].get('username')
        if not username:
            return jsonify({'success': False, 'error': {'description': 'Username is required'}})
        response = create_user(username, password=password, group=group)
    else:
        response = update_user(username, password=password, group=group)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})

@users_bp.route('/delete', methods=['POST'])
@login_required(group='full')
def delete():
    req: dict = request.json
    if not req:
        abort(400, description=get_translate('errors.admin.tables.missing_request_data'))

    active_username = session.get('username')
    username = req.get('id')

    if username == active_username:
        return jsonify({'success': False, 'error': {'description': "You can't delete your self"}})
    
    response = delete_user(username)
    status = response.get('status')
    if status == 'NOT_FOUND':
        return jsonify({'success': False, 'error': {'description': 'User not found'}})

    return jsonify({'success': True})
