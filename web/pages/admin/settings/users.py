from flask import Blueprint, jsonify, render_template, request, session

from core.admin.repository import create_user, delete_user, update_user
from core.admin.tables.settings.users import get_users
from core.utils import json
from web.pages.admin.utils import login_required


users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('', methods=['GET'])
@login_required
def index():
    users = get_users()

    template = render_template(
        'admin/settings/users.html',
        users=users,
    )
    
    return template


@users_bp.route('/get', methods=['GET'])
@login_required
def get():
    users = get_users()

    template = jsonify({'success': True, 'data': users})
    
    return template


@users_bp.route('/add', methods=['POST'])
@login_required
def add():
    data: dict = request.json

    username = data.get('username')
    password = data.get('password')
    access = {}

    json_access = data.get('access', None)
    if json_access:
        access = json.loads(json_access)
        
    response = create_user(username, password, access)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})


@users_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json

    username = data.get('username')
    password = data.get('password', None)
    access = {}

    json_access = data.get('access', None)
    if json_access:
        access = json.loads(json_access)

    response = update_user(username, password, access)
    status = response.get('status')
    if status == 'OK':
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': {'description': status}})


@users_bp.route('/delete', methods=['POST'])
@login_required
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
