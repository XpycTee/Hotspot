from contextlib import contextmanager
from dataclasses import asdict
import threading
from core.bootstrap.env import REDIS_URL
from core.config.configurator import Configurator
from core.config.models import AppConfig
from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.utils import json


from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select


class ConfigLoader:
    def __init__(self, redis: Redis | None = None):
        if redis is None:
            try:
                self._r = Redis.from_url(REDIS_URL, decode_responses=True)
                self._r.ping()
            except (RedisError, OSError):
                self._r = None
        else:
            self._r = redis

    @contextmanager
    def update(self):
        config = self.load()

        pre_up = asdict(config)
        yield config
        post_up = asdict(config)

        if pre_up != post_up:
            self.save(config)

    def load(self):
        config = self._r.get('app:config') if self._r else None
        cache_config = json.loads(config) if config else {}
        if cache_config:
            return Configurator(cache_config).create()
        
        with get_session() as db_session:
            db_config = db_session.scalars(select(SystemConfig)).first()
            if db_config is None:
                default_cfg = Configurator().create()
                default_db_config = SystemConfig(data=default_cfg)
                db_session.add(default_db_config)
                return default_cfg

            return Configurator(db_config.data, db_config.version).create()

    def save(self, config: AppConfig):
        with get_session() as db_session:
            db_config = db_session.scalars(select(SystemConfig)).first()
            if db_config is None:
                db_versoin = 1
                config.version = db_versoin
                db_config = SystemConfig(data=config, version=db_versoin)
                db_session.add(db_config)
            else:
                db_config.version += 1
                db_versoin = db_config.version
                config.version = db_versoin
                db_config.data = config
                
        if self._r:
            self._r.set('app:config', json.dumps(config))
            self._r.publish('config:update', json.dumps({'version': db_versoin}))


class ConfigRuntime:
    def __init__(self):
        self._lock = threading.RLock()
        self._config: AppConfig | None = None
        self._version = -1

    @property
    def version(self):
        return self._version

    def get(self) -> AppConfig:
        if self._config is None or self._version < 0:
            self._reload()
        return self._config

    def _reload(self):
        with self._lock:
            cfg = ConfigLoader().load()

            if self._version >= cfg.version:
                return

            self._config = cfg
            self._version = cfg.version

    def force_reload(self):
        with self._lock:
            self._version = -1
