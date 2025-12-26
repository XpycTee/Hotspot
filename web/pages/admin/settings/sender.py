from flask import Blueprint, jsonify, render_template, request

from core.config import CONFIG, ConfigStore
from web.pages.admin.utils import login_required


sender_bp = Blueprint('sender', __name__, url_prefix='/sender')


@sender_bp.route('', methods=['GET'])
@login_required
def index():

    template = render_template(
        'admin/settings/sender.html',
        sender=CONFIG.sender
    )
    
    return template

@sender_bp.route('/update', methods=['POST'])
@login_required
def update():
    data: dict = request.json

    CONFIG.sender.type = data.get('type')
    CONFIG.sender.api_key = data.get('api_key', None)
    CONFIG.sender.url = data.get('url', None)

    store = ConfigStore('sender')
    store.save()

    return jsonify({'success': True})
