from sqlalchemy import select
import yaml
import yaml_include

from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.redis import cache


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))

def get_config() -> tuple:
    return get_config_from_yaml()


def get_config_from_yaml() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings: dict = yaml.full_load(f)
    return settings.get('settings', {}), 0


def get_config_from_db() -> dict:
    with get_session() as db_session:
        db_config = db_session.scalars(select(SystemConfig)).first()
        config = db_config.data
    return (config or {}, db_config.version)


def get_config_fromn_redis() -> dict:
    config = cache.get('app:config', {})
    return config, 0
