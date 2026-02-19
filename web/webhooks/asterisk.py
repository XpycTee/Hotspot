from flask import Blueprint, Response, request

from core.logging import get_logger
from core.redis import cache


asterisk_bp = Blueprint('asterisk', __name__, url_prefix='/asterisk')

logger = get_logger('web.webhooks.asterisk')

@asterisk_bp.route('', methods=['GET'])
def index():
    api_key = request.args.get('api_key')
    if not api_key:
        return Response('Bad api key', status=403)
    
    phone = request.args.get('phone')

    request_id = cache.get(f'callcheck:asterisk:phone:{phone}')
    phone_data = cache.get(f'callcheck:asterisk:id:{request_id}')
    if phone_data is None:
        logger.error('Callcheck not found')
        return Response('Callcheck not found', status=404)
    
    check_status = phone_data.get('status')
    if not check_status:
        phone_data['status'] = True
        cache.set(f'callcheck:asterisk:id:{request_id}', phone_data, 300)

    return Response('OK', status=200)
