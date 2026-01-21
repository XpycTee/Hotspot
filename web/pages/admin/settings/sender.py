from flask import Blueprint, jsonify, render_template, request

from core.config.store import ConfigLoader
from web.pages.admin.utils import login_required


sender_bp = Blueprint('sender', __name__, url_prefix='/sender')


@sender_bp.route('', methods=['GET'])
@login_required(group='full')
def index():

    template = render_template(
        'admin/settings/sender.html',
        sender=ConfigLoader().load().sender
    )
    
    return template

@sender_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    data: dict = request.json

    with ConfigLoader().update() as config:
        config.sender.type = data.get('type')
        config.sender.api_key = data.get('api_key', None)
        config.sender.url = data.get('url', None)

    return jsonify({'success': True})
