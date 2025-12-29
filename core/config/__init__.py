from sqlalchemy import select
import yaml
import yaml_include

from core.config.configurator import Configurator
from core.database.models.settings import SystemConfig
from core.database.session import get_session
from core.redis import cache


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))


def get_config_from_yaml() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        config: dict = yaml.full_load(f)

    result = Configurator(config.get('settings'), 0).create()
    return result


def load_config_from_db():
    with get_session() as db_session:
        db_config = db_session.scalars(select(SystemConfig)).first()

        if db_config is None:
            default_cfg = Configurator().create()

            default_db_config = SystemConfig(data=default_cfg)
            db_session.add(default_db_config)
            db_session.commit()
            
            return default_cfg
            
        result = Configurator(db_config.data, db_config.version).create()
    return result


def get_config_from_redis() -> dict:
    config = cache.get('app:config', {})
    version = config.get('version', 0)
    result = Configurator(config, version).create()
    return result


CONFIG = load_config_from_db()
