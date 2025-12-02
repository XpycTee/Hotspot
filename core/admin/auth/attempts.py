from core.cache import get_cache


def increment_attempts(session_id):
    cache = get_cache()
    cache.inc(f'admin:login:attempts:{session_id}')
    return cache.get(f'admin:login:attempts:{session_id}')


def reset_attempts(session_id):
    cache = get_cache()
    cache.delete(f'admin:login:attempts:{session_id}')
    cache.delete(f'admin:login:lockout:{session_id}')
