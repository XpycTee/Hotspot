import hashlib
import re
import secrets
import time
from flask import Blueprint, Response, request

from core.config import get_config
from core.config.models.verificators import VProviderType
from core.redis import get_cache
from web import logger


smsru_bp = Blueprint('smsru', __name__, url_prefix='/smsru')
CALLCHECK_CACHE_TTL_SECONDS = 600
REPLAY_WINDOW_SECONDS = 600
TIMESTAMP_SKEW_SECONDS = 300
_DATA_KEY_RE = re.compile(r'^data\[(\d+)\]$')
_api_key_cache: str | None = None
_api_key_cache_deadline: float = 0.0


def _get_smsru_api_key() -> str | None:
    global _api_key_cache, _api_key_cache_deadline
    now = time.monotonic()
    if _api_key_cache is not None and now < _api_key_cache_deadline:
        return _api_key_cache

    config = get_config()
    for provider in config.verificators.items:
        if provider.type != VProviderType.SMSRU or not provider.enabled:
            continue
        for field in provider.fields:
            if field.name == "api_key" and field.value:
                _api_key_cache = field.value
                _api_key_cache_deadline = now + 30.0
                return _api_key_cache

    _api_key_cache = None
    _api_key_cache_deadline = now + 5.0
    return None


def _parse_entries(post_data) -> dict[int, str]:
    indexed_data: dict[int, str] = {}
    for key, value in post_data.items():
        match = _DATA_KEY_RE.fullmatch(key)
        if not match:
            continue
        indexed_data[int(match.group(1))] = value
    return indexed_data


def _parse_callcheck_entry(entry: str) -> dict | None:
    lines = entry.splitlines()
    if len(lines) < 4 or lines[0] != "callcheck_status":
        return None

    try:
        check_id = lines[1]
        check_status = int(lines[2])
        unix_timestamp = float(lines[3])
    except (ValueError, TypeError):
        return None

    if abs(time.time() - unix_timestamp) > TIMESTAMP_SKEW_SECONDS:
        return None

    return {
        'check_id': check_id,
        'check_status': check_status,
        'unix_timestamp': unix_timestamp,
    }


@smsru_bp.route('', methods=['POST'])
def index():
    post = request.form

    received_hash = post.get('hash')
    indexed_data = _parse_entries(post)

    api_key = _get_smsru_api_key()
    if not api_key:
        logger.error("smsru webhook: api key missing")
        return Response("100", status=503)

    if not indexed_data:
        logger.error("smsru webhook: data missing")
        # smsru's error
        return Response("data missing", status=400)

    if not received_hash:
        logger.error("smsru webhook: hash missing")
        # smsru's error
        return Response("hash missing", status=400)

    payload_entries = [indexed_data[i] for i in sorted(indexed_data)]
    concat_data = "".join(payload_entries)

    calculated_hash = hashlib.sha256(
        (api_key + concat_data).encode("utf-8")
    ).hexdigest()

    if not secrets.compare_digest(calculated_hash, received_hash):
        logger.error("smsru webhook: invalid hash")
        # Local error
        return Response("100", status=403)

    replay_key = f'webhook:smsru:hash:{received_hash}'
    with get_cache() as cache:
        if cache.has(replay_key):
            logger.warning("smsru webhook: replay detected")
            return Response("100", status=200)
        cache.set(replay_key, 1, REPLAY_WINDOW_SECONDS)

    for entry in payload_entries:
        confirm_data = _parse_callcheck_entry(entry)
        if confirm_data is None:
            continue

        check_id = confirm_data['check_id']
        with get_cache() as cache:
            cache_key = f'callcheck:smsru:id:{check_id}'
            cached_data = cache.get(cache_key)
            if not isinstance(cached_data, dict):
                logger.warning("smsru webhook: callcheck cache not found", extra={'check_id': check_id})
                continue

            cached_data['confirm'] = confirm_data
            cache.set(cache_key, cached_data, CALLCHECK_CACHE_TTL_SECONDS)

    return Response("100", status=200)
