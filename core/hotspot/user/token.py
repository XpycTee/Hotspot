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
    pop_lua = """
    local val = redis.call('GET', KEYS[1])
    if val then
        redis.call('DEL', KEYS[1])
    end
    return val
    """
    cache_token = cache.eval(pop_lua, 1, f"auth:token:{phone_number}") or ""
    return cache_token
