from flask import Blueprint, jsonify, render_template, request

from core.admin.tables.settings.users import get_users
from core.config.store import ConfigLoader
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

@users_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json


    return jsonify({'success': True})
