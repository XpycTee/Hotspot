from dataclasses import dataclass, field
from datetime import timedelta
from core.utils import json
import os
from typing import Dict, List, Optional


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


@dataclass(frozen=True)
class RemoteHost:
    """Remote RADIUS capable host we can talk to.

    Args:
        address (str): IP address.
        secret (bytes): RADIUS secret. If connecting to a RadSec server, the secret should be `radsec`.
        name (str): Short name (used for logging only).
        authport (int): Port used for authentication packets.
        acctport (int): Port used for accounting packets.
        coaport (int): Port used for CoA packets.
    """

    address: str
    secret: bytes
    name: str
    authport: int = 1812
    acctport: int = 1813
    coaport: int = 3799


@dataclass
class RadiusConfig:
    """
    RADIUS server configuration.
    """

    enabled: bool = True
    addresses: List[str] = field(default_factory=list)
    ports: RadiusPortsConfig = field(default_factory=RadiusPortsConfig)
    hosts: Dict[str, RemoteHost] = field(default_factory=RemoteHost)
    

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

    def get_delay(self, is_staff: bool) -> timedelta:
        if is_staff:
            return self.staff.delay
        return self.guest.delay


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
    sender: SenderConfig
    admin: AdminConfig
    radius: RadiusConfig

    #: Global configuration version (DB-backed)
    version: int
