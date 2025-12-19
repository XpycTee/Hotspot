from core.redis import cache


def increment_attempts(session_id):
    return cache.incr(f'admin:login:attempts:{session_id}')


def reset_attempts(session_id):
    cache.delete(f'admin:login:attempts:{session_id}')
    cache.delete(f'admin:login:lockout:{session_id}')
