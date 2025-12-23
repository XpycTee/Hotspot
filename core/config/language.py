from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import LanguageConfig


def get_lang_config() -> LanguageConfig:
    config = get_config()
    raw = config.get('data', {})
    version = config.get('version', 0)
    data = ConfigLoader(raw, version).language()
    return data


config = get_lang_config()
LANGUAGE = config.language
LANGUAGE_CONTENT = config.content
