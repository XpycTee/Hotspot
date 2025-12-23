from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import RadiusConfig


def get_radius_config() -> RadiusConfig:
    raw, version = get_config()
    data = ConfigLoader(raw, version).radius()
    return data


RADIUS = get_radius_config()
