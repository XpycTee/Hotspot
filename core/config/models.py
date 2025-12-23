from dataclasses import dataclass, field
from datetime import timedelta
import json
import os
from typing import Dict, List, Optional

from pyrad2 import server


@dataclass
class LanguageConfig:
    language: str
    _content: dict = None

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
                with open(file_path, 'r', encoding='utf-8') as lang_file:
                    language_content[language_name] = json.load(lang_file)
        self._content = language_content
        return language_content


@dataclass
class LoggingConfig:
    level: int
    is_gunicorn: bool


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

    username: str
    password_hash: bytes
    max_login_attempts: int
    lockout_time: timedelta


@dataclass(frozen=True)
class RadiusPortsConfig:
    """
    RADIUS service ports configuration.
    """

    auth: int = 1812
    acct: int = 1813
    coa: int = 3799


@dataclass
class RadiusConfig:
    """
    RADIUS server configuration.
    """

    enabled: bool = True
    addresses: List[str] = field(default_factory=list)
    ports: RadiusPortsConfig = field(default_factory=RadiusPortsConfig)

    #: Optional per-host configuration (loaded from DB)
    hosts: Dict[str, server.RemoteHost] = field(default_factory=server.RemoteHost)

    #: Configuration version for synchronization and hot-reload
    version: int = 0


@dataclass(frozen=True)
class HotspotUserConfig:
    """
    Per-user hotspot configuration.
    """

    password: str
    delay: timedelta


@dataclass
class HotspotConfig:
    """
    Hotspot runtime configuration.
    """

    online_timeout: timedelta
    staff: HotspotUserConfig
    guest: HotspotUserConfig


@dataclass(frozen=True)
class SenderConfig:
    """
    External message sender configuration (SMS, HTTP API, etc).
    """

    type: str
    url: Optional[str] = None
    api_key: Optional[str] = None

    @property
    def params(self):
        if self.url is not None:
            return {'url': self.url}
        if self.api_key is not None:
            return {'api_key': self.api_key}
        return {}


@dataclass
class Config:
    """
    Root application configuration object.

    This object represents the fully resolved runtime configuration
    after merging:
        - database configuration
        - environment variables
        - default values
    """

    language: LanguageConfig
    logging: LoggingConfig
    hotspot: HotspotConfig
    sender: SenderConfig
    admin: AdminConfig
    radius: RadiusConfig

    #: Global configuration version (DB-backed)
    version: int