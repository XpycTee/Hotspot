from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import RadiusConfig


def get_radius_config() -> RadiusConfig:
    raw = get_config()
    data = ConfigLoader(raw).radius()
    return data


RADIUS = get_radius_config()
