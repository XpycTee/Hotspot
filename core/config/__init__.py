from sqlalchemy import select
import yaml
import yaml_include

from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.redis import cache


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))

def get_config() -> dict:
    return get_config_from_yaml()


def get_config_from_yaml() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        config: dict = yaml.full_load(f)
    result = {'data': config, 'version': 0}
    return result


def get_config_from_db() -> dict:
    with get_session() as db_session:
        db_config = db_session.scalars(select(SystemConfig)).first()
        result = db_config.to_dict()
    return result


def get_config_from_redis() -> dict:
    result = cache.get('app:config', {})
    return result
