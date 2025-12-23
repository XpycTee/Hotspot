from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import RadiusConfig


def get_radius_config() -> RadiusConfig:
    config = get_config()
    raw = config.get('data', {})
    version = config.get('version', 0)
    data = ConfigLoader(raw, version).radius()
    return data


RADIUS = get_radius_config()
