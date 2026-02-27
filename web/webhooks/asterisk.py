import secrets
import time

from flask import Blueprint, Response, request

from core.config import get_config
from core.config.models.verificators import VProviderType
from core.logging import get_logger
from core.redis import get_cache
from core.utils.phone import normalize_phone


asterisk_bp = Blueprint('asterisk', __name__, url_prefix='/asterisk')

logger = get_logger('web.webhooks.asterisk')
CALLCHECK_CACHE_TTL_SECONDS = 300
REPLAY_WINDOW_SECONDS = 120
_api_key_cache: str | None = None
_api_key_cache_deadline: float = 0.0


def _get_expected_api_key() -> str | None:
    global _api_key_cache, _api_key_cache_deadline
    now = time.monotonic()
    if _api_key_cache is not None and now < _api_key_cache_deadline:
        return _api_key_cache

    config = get_config()
    for provider in config.verificators.items:
        if provider.type != VProviderType.ASTERISK or not provider.enabled:
            continue
        for field in provider.fields:
            if field.name == "api_key" and field.value:
                _api_key_cache = field.value
                _api_key_cache_deadline = now + 30.0
                return _api_key_cache

    _api_key_cache = None
    _api_key_cache_deadline = now + 5.0
    return None


def _extract_payload() -> tuple[str | None, str | None, str | None]:
    payload = request.get_json(silent=True) or {}
    api_key = (
        request.headers.get('X-Webhook-Token')
        or payload.get('api_key')
        or request.values.get('api_key')
    )
    phone = payload.get('phone') or request.values.get('phone')
    event_id = payload.get('event_id') or request.values.get('event_id')
    return api_key, phone, event_id


@asterisk_bp.route('', methods=['GET', 'POST'])
def index():
    expected_key = _get_expected_api_key()
    if not expected_key:
        logger.error('asterisk webhook: provider api key is not configured')
        return Response('Service unavailable', status=503)

    api_key, phone, event_id = _extract_payload()
    if not api_key or not secrets.compare_digest(api_key, expected_key):
        return Response('Bad api key', status=403)

    normalized_phone = normalize_phone(phone or '')
    if not normalized_phone:
        return Response('Bad phone', status=400)

    with get_cache() as cache:
        request_id = cache.get(f'callcheck:asterisk:phone:{normalized_phone}')
        if not request_id:
            logger.warning('asterisk webhook: callcheck request id not found')
            return Response('Callcheck not found', status=404)

        if event_id:
            replay_key = f'webhook:asterisk:phone:{normalized_phone}:event:{event_id}'
            if cache.has(replay_key):
                logger.warning('asterisk webhook: replay detected')
                return Response('OK', status=200)
            cache.set(replay_key, 1, REPLAY_WINDOW_SECONDS)

        phone_data = cache.get(f'callcheck:asterisk:id:{request_id}')
        if phone_data is None:
            logger.warning('asterisk webhook: callcheck data not found')
            return Response('Callcheck not found', status=404)

        check_status = phone_data.get('status')
        if not check_status:
            phone_data['status'] = True
            cache.set(f'callcheck:asterisk:id:{request_id}', phone_data, CALLCHECK_CACHE_TTL_SECONDS)

    return Response('OK', status=200)
