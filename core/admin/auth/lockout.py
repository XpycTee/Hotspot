from core.cache import cache

from datetime import datetime, timedelta

from core.config.admin import ADMIN


def check_lockout(session_id):
    lockout_until = cache.get(f'admin:login:lockout:{session_id}')
    if lockout_until is None:
        return False
    
    now_timestamp = datetime.now().timestamp()
    return (lockout_until and now_timestamp < float(lockout_until))


def update_lockout(session_id):
    lockout_time = ADMIN.get('lockout_time')
    lockout_delta = timedelta(minutes=lockout_time)
    lockout_until = datetime.now() + lockout_delta
    cache.set(f'admin:login:lockout:{session_id}', lockout_until.timestamp(), lockout_delta.total_seconds())