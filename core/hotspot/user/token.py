import secrets
from core.redis import get_cache


def generate_token(phone_number):
    token = secrets.token_hex(32)
    with get_cache() as cache:
        cache.set(f"auth:token:{phone_number}", token, 60)
    return token


def check_token(phone_number, token):
    with get_cache() as cache:
        cache_token = cache.get(f"auth:token:{phone_number}")
    return token == cache_token


def get_token(phone_number):
    with get_cache() as cache:
        cache_token = cache.pop(f"auth:token:{phone_number}")
    return cache_token
