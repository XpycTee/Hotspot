import secrets
from core.cache import cache


def generate_token(phone_number):
    token = secrets.token_hex(32)
    cache.set(f"auth:token:{phone_number}", token, 60)
    return token


def check_token(phone_number, token):
    cache_token = cache.get(f"auth:token:{phone_number}") or ""
    return token == cache_token


def get_token(phone_number):
    cache_token = cache.get(f"auth:token:{phone_number}") or ""
    return cache_token
