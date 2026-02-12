from core.redis import cache


def auth_confirm(user_fp):
    cache.set(f'auth:confirmed:{user_fp}', True, 60)

def check_confirm(user_fp):
    confirmed = cache.get(f'auth:confirmed:{user_fp}')
    return confirmed is not None and confirmed
