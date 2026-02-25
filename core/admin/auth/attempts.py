from core.redis import get_cache


def increment_attempts(session_id):
    with get_cache() as cache:
        return cache.incr(f'admin:login:attempts:{session_id}')


def reset_attempts(session_id):
    with get_cache() as cache:
        cache.delete(f'admin:login:attempts:{session_id}')
        cache.delete(f'admin:login:lockout:{session_id}')
