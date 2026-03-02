from core.config import get_config
from core.redis import get_cache

from datetime import datetime



def check_lockout(session_id):
    with get_cache() as cache:
        lockout_until = cache.get(f'admin:login:lockout:{session_id}')

    if lockout_until is None:
        return None

    return datetime.now().timestamp() < float(lockout_until)


def update_lockout(session_id):
    config = get_config()
    lockout_time = config.admin.lockout_time
    lockout_until = datetime.now() + lockout_time
    with get_cache() as cache:
        cache.set(
            f'admin:login:lockout:{session_id}',
            lockout_until.timestamp(),
            int(lockout_time.total_seconds()),
        )
