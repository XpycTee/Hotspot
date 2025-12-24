from dataclasses import asdict
from redis import Redis
from sqlalchemy import select
import yaml
import yaml_include

from core.bootstrap.env import REDIS_URL
from core.config.loader import ConfigLoader
from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.redis import cache
from core.utils import json


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))


class ConfigStore:
    def __init__(self, domain: str, redis: Redis | None = None):
        if redis is None:
            self._r = Redis.from_url(REDIS_URL, decode_responses=True)
        else:
            self._r = redis
        self._domain = domain

    def load(self):
        config = self._r.get('app:config')
        data = json.loads(config) if config else {}
        return data.get(self._domain)

    def save(self):
        CONFIG.version += 1

        with get_session() as db_session:
            db_config = db_session.scalars(select(SystemConfig)).first()
            db_config.data = CONFIG
            db_session.commit()

        self._r.set('app:config', json.dumps(CONFIG))
        self._r.publish('config:update', json.dumps({'version': CONFIG.version, 'domain': self._domain}))


def get_config_from_yaml() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        config: dict = yaml.full_load(f)

    result = ConfigLoader(config.get('settings'), 0).load()
    return result


def load_config_from_db():
    with get_session() as db_session:
        db_config = db_session.scalars(select(SystemConfig)).first()

        if db_config is None:
            default_cfg = ConfigLoader().load()

            default_db_config = SystemConfig(data=default_cfg)
            db_session.add(default_db_config)
            db_session.commit()
            
            return default_cfg
            
        result = ConfigLoader(db_config.data, db_config.version).load()
    return result


def get_config_from_redis() -> dict:
    config = cache.get('app:config', {})
    version = config.get('version', 0)
    result = ConfigLoader(config, version).load()
    return result


CONFIG = load_config_from_db()
