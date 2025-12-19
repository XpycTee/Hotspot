from core.redis import cache

from datetime import datetime, timedelta

from core.config.admin import ADMIN


def check_lockout(session_id):
    lockout_until = cache.get(f'admin:login:lockout:{session_id}')
    return lockout_until and datetime.now().timestamp() < lockout_until


def update_lockout(session_id):
    lockout_time = ADMIN.get('lockout_time')
    lockout_until = datetime.now() + timedelta(minutes=lockout_time)
    cache.set(f'admin:login:lockout:{session_id}', lockout_until.timestamp(), lockout_time * 60)