from core.redis import get_cache


def auth_confirm(user_fp):
    with get_cache() as cache:
        cache.set(f'auth:confirmed:{user_fp}', True, 60)

def check_confirm(user_fp):
    with get_cache() as cache:
        confirmed = cache.get(f'auth:confirmed:{user_fp}')
    return confirmed is not None and confirmed
