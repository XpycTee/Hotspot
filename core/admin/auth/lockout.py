from core.config import get_config
from core.redis import cache

from datetime import datetime



def check_lockout(session_id):
    lockout_until = cache.get(f'admin:login:lockout:{session_id}')
    return lockout_until and datetime.now().timestamp() < lockout_until


def update_lockout(session_id):
    config = get_config()
    lockout_time = config.admin.lockout_time
    lockout_until = datetime.now() + lockout_time
    cache.set(f'admin:login:lockout:{session_id}', lockout_until.timestamp(), lockout_time * 60)