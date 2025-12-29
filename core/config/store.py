from contextlib import contextmanager
import threading
from core.bootstrap.env import REDIS_URL
from core.config.configurator import Configurator
from core.config.models import AppConfig
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

    @contextmanager
    def update(self):
        config = self.load()
        yield config
        self.save(config)

    def load(self):
        config = self._r.get('app:config')
        data = json.loads(config) if config else {}
        if not data:
            with get_session() as db_session:
                db_config = db_session.scalars(select(SystemConfig)).first()
                data = db_config.data if db_config else {}

        return Configurator(data).create()

    def save(self, config: AppConfig):
        config.version += 1

        with get_session() as db_session:
            db_config = db_session.scalars(select(SystemConfig)).first()
            db_config.data = config

        self._r.set('app:config', json.dumps(config))
        self._r.publish('config:update', json.dumps({'version': config.version}))


class ConfigRuntime:
    def __init__(self):
        self._lock = threading.RLock()
        self._config: AppConfig | None = None
        self.version = -1

    def get(self) -> AppConfig:
        if self._config is None:
            self.reload()
        return self._config

    def reload(self):
        with self._lock:
            cfg = ConfigStore().load()

            if self.version >= cfg.version:
                return

            self._config = cfg
            self.version = cfg.version
