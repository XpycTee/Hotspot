from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import AdminConfig


def get_admin_config() -> AdminConfig:
    config = get_config()
    raw = config.get('data', {})
    version = config.get('version', 0)
    data = ConfigLoader(raw, version).admin()
    return data


ADMIN = get_admin_config()
