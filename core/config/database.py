from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import DatabaseConfig


def get_db_config() -> DatabaseConfig:
    raw = get_config()
    data = ConfigLoader(raw).db()
    return data
