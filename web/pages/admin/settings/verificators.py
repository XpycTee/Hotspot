from flask import Blueprint, jsonify, render_template, request

from core.config import get_config
from core.config.models import SenderConfig
from core.config.store import ConfigLoader
from web.pages.admin.utils import login_required


verificators_bp = Blueprint('verificators', __name__, url_prefix='/verificators')


@verificators_bp.route('', methods=['GET'])
@login_required(group='full')
def index():
    config = get_config()
    verificators = [
        {
            "id": "smsru", 
            "name": "sms.ru", 
            "enabled": True, 
            "fields": [
                {"name": "api_key", "label": "API Key", "type": "password", "value": "qwerty"},
            ],
        },
        {
            "id": "asterisk", 
            "name": "Asterisk", 
            "enabled": False, 
            "fields": [
                {"name": "call_phone", "label": "Call phone", "type": "text", "value": "79999999999"},
            ],
        },
        {
            "id": "mikrotik", 
            "name": "Mikrotik", 
            "enabled": False, 
            "fields": [
                {"name": "url", "label": "URL", "type": "text", "value": "https://admin:pass@router.lan/?interface=lte1"},
            ],
        },
        {
            "id": "huawei", 
            "name": "Huawei", 
            "enabled": False, 
            "fields": [
                {"name": "url", "label": "URL", "type": "text", "value": "http://username:password@192.168.8.1/"},
            ],
        },
    ]

    template = render_template(
        'admin/settings/verificators.html',
        verificators=verificators,
    )
    
    return template


@verificators_bp.route('/update', methods=['POST'])
@login_required(group='full')
def update():
    data: dict = request.json
        
    return jsonify({'success': True})
