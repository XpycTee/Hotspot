from core.config import get_config
from core.config.loader import ConfigLoader
from core.config.models import LanguageConfig


def get_lang_config() -> LanguageConfig:
    raw, version = get_config()
    data = ConfigLoader(raw, version).language()
    return data


config = get_lang_config()
LANGUAGE = config.language
LANGUAGE_CONTENT = config.content
