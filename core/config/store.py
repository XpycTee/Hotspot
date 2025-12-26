from core.bootstrap.env import REDIS_URL
from core.config import CONFIG
from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.utils import json


from redis import Redis
from sqlalchemy import select


class ConfigStore:
    def __init__(self, redis: Redis | None = None):
        if redis is None:
            self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        else:
            self._r = redis

    def load(self):
        config = self._r.get('app:config')
        data = json.loads(config) if config else {}
        return data

    def save(self):
        CONFIG.version += 1

        with get_session() as db_session:
            db_config = db_session.scalars(select(SystemConfig)).first()
            db_config.data = CONFIG
            db_session.commit()

        self._r.set('app:config', json.dumps(CONFIG))
        self._r.publish('config:update', json.dumps({'version': CONFIG.version}))
