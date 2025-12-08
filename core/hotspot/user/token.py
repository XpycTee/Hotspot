import secrets
from core.cache import get_cache


def generate_token(phone_number):
    cache = get_cache()
    token = secrets.token_hex(32)
    cache.set(f"auth:token:{phone_number}", token)
    return token


def check_token(phone_number, token):
    cache = get_cache()
    cache_token = cache.get(f"auth:token:{phone_number}") or ""
    return token == cache_token


def get_token(phone_number):
    cache = get_cache()
    cache_token = cache.get(f"auth:token:{phone_number}") or ""
    return cache_token
