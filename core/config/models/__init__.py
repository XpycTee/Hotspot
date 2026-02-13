from dataclasses import dataclass, field
from datetime import timedelta
from core.config.models.hotspot import HotspotConfig
from core.config.models.radius import RadiusConfig
from core.config.models.verificators import CallcheckConfig, SenderConfig, VerificationProvider
from core.utils import json
import os
from typing import List, Optional


@dataclass
class LanguageConfig:
    name: str
    _content: dict = field(default=None, metadata={"json": False})

    @property
    def content(self) -> dict:
        if self._content:
            return self._content
        
        language_folder = 'web/static/language'
        language_content = {}
        for filename in os.listdir(language_folder):
            if filename.endswith('.json'):
                file_path = os.path.join(language_folder, filename)
                language_name = os.path.splitext(filename)[0]
                with open(file_path, 'rb') as lang_file:
                    language_content[language_name] = json.load(lang_file)
        self._content = language_content
        return language_content


@dataclass(frozen=True)
class DatabaseConfig:
    url: str


@dataclass(frozen=True)
class RedisConfig:
    url: str


@dataclass(frozen=True)
class AdminConfig:
    """
    Configuration for administrative access to the system.
    """

    max_login_attempts: int
    lockout_time: timedelta
    

@dataclass
class AppConfig:
    """
    System application configuration object.

    This object represents the fully resolved runtime configuration
    after merging:
        - database configuration
        - environment variables
        - default values
    """

    language: LanguageConfig
    hotspot: HotspotConfig
    sender: Optional[SenderConfig] # Legacy
    callcheck: Optional[CallcheckConfig] # Legacy
    verificators: List[VerificationProvider]
    admin: AdminConfig
    radius: RadiusConfig

    #: Global configuration version (DB-backed)
    version: int
