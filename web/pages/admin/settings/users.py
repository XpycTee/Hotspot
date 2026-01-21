from flask import Blueprint, jsonify, render_template, request, session

from core.admin.auth.security import check_password
from core.admin.repository import create_user, delete_user, update_user
from core.admin.tables.settings.users import get_users
from core.utils import json
from web.pages.admin.utils import login_required


users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    users = get_users()

    template = render_template(
        'admin/settings/users.html',
        users=users,
    )
    
    return template


@users_bp.route('/get', methods=['GET'])
@login_required(group='full')
def get():
    users = get_users()

    template = jsonify({'success': True, 'data': users})
    
    return template


@users_bp.route('/add', methods=['POST'])
@login_required(group='full')
def add():
    data: dict = request.json

    username = data.get('username').strip()
    password = data.get('password').strip()
    password_confirm = data.get('password_confirm').strip()

    if password != password_confirm:
        jsonify({'success': False, 'error': {'description': 'Passwords do not match'}})

    group = data.get('group')
        
    response = create_user(username, password, group)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})


@users_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    data: dict = request.json

    active_username = session.get('username')
    username = data.get('username')

    if username == active_username:
        return jsonify({'success': False, 'error': {'description': "You can't update your group"}})
    
    group = data.get('group', None)

    response = update_user(username, group=group)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})


@users_bp.route('/change_password', methods=['POST'])
@login_required(group='full')
def change_password():
    data: dict = request.json

    username = data.get('username')

    active_username = session.get('username')
    confirm_action_password = data.get('confirm').strip()

    if not check_password(active_username, confirm_action_password):
        jsonify({'success': False, 'error': {'description': 'Wrong password'}})

    password = data.get('password').strip()
    password_confirm = data.get('password_confirm').strip()

    if password != password_confirm:
        jsonify({'success': False, 'error': {'description': 'Passwords do not match'}})

    response = update_user(username, password=password)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})


@users_bp.route('/delete', methods=['POST'])
@login_required(group='full')
def delete():
    data: dict = request.json

    active_username = session.get('username')
    username = data.get('username')

    if username == active_username:
        return jsonify({'success': False, 'error': {'description': "You can't delete your self"}})
    
    response = delete_user(username)
    status = response.get('status')
    if status == 'NOT_FOUND':
        return jsonify({'success': False, 'error': {'description': 'User not found'}})

    return jsonify({'success': True})
