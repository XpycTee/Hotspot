from flask import Blueprint, Response, request

from core.config import get_config
from core.config.models.verificators import VProviderType
from core.logging import get_logger
from core.redis import get_cache


asterisk_bp = Blueprint('asterisk', __name__, url_prefix='/asterisk')

logger = get_logger('web.webhooks.asterisk')

@asterisk_bp.route('', methods=['GET'])
def index():
    api_key = request.args.get('api_key')
    if not api_key:
        return Response('Bad api key', status=403)

    phone = request.args.get('phone')
    if not phone:
        return Response('Bad phone', status=400)

    config = get_config()
    expected_key = None
    for provider in config.verificators.items:
        if provider.type != VProviderType.ASTERISK or not provider.enabled:
            continue
        for field in provider.fields:
            if field.name == "api_key" and field.value:
                expected_key = field.value
                break
        if expected_key:
            break

    if expected_key and api_key != expected_key:
        return Response('Bad api key', status=403)

    with get_cache() as cache:
        request_id = cache.get(f'callcheck:asterisk:phone:{phone}')
        if not request_id:
            logger.error('Callcheck request id not found')
            return Response('Callcheck not found', status=404)

        phone_data = cache.get(f'callcheck:asterisk:id:{request_id}')
        if phone_data is None:
            logger.error('Callcheck not found')
            return Response('Callcheck not found', status=404)
        
        check_status = phone_data.get('status')
        if not check_status:
            phone_data['status'] = True
            cache.set(f'callcheck:asterisk:id:{request_id}', phone_data, 300)

    return Response('OK', status=200)
