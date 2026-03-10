import secrets
from core.redis import get_cache


def _normalize_mac(mac: str) -> str:
    if not mac:
        return ''
    return mac.strip().replace('-', ':').lower()


def _token_key(identity: str) -> str:
    # Identity can be MAC (new flow) or phone (legacy flow during rollout).
    return f"auth:token:{_normalize_mac(identity)}"


def _trial_token_key(identity: str) -> str:
    return f"auth:trial:{_normalize_mac(identity)}"


def generate_token(mac):
    token = secrets.token_hex(32)
    with get_cache() as cache:
        cache.set(_token_key(mac), token, 3600)
    return token


def generate_trial_token(mac, ttl=300):
    token = secrets.token_hex(32)
    with get_cache() as cache:
        cache.set(_trial_token_key(mac), token, ttl)
    return token


def check_token(mac, token):
    with get_cache() as cache:
        cache_token = cache.get(_token_key(mac))
    return token == cache_token


def get_token(mac):
    with get_cache() as cache:
        cache_token = cache.get(_token_key(mac))
    return cache_token


def get_trial_token(mac):
    with get_cache() as cache:
        cache_token = cache.get(_trial_token_key(mac))
    return cache_token


def delete_trial_token(mac):
    with get_cache() as cache:
        cache.delete(_trial_token_key(mac))
