from datetime import timedelta
import logging
import os
import bcrypt
from environs import Env

from pyrad2 import server

from core.config.models import (
    AdminConfig,
    Config,
    HotspotConfig,
    HotspotUserConfig,
    LanguageConfig,
    LoggingConfig, 
    RadiusConfig, 
    RadiusPortsConfig,
    SenderConfig
)

from core.config.defaults import *


class ConfigLoader:
    def __init__(self, settings: dict | None, version: int = 0):
        self._settings = settings or {}
        self._version = version
        self._env = Env(prefix='HOTSPOT_')
        self._env.read_env()

    @staticmethod
    def _hashpw(password: str):
        password_hash = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt(),
        )
        return password_hash

    @staticmethod
    def _convert_delay(delay):
        if isinstance(delay, int):
            return timedelta(seconds=delay)
        
        suffixes = {
            'w': 'weeks',
            'd': 'days',
            'h': 'hours',
            'm': 'minutes',
            's': 'seconds'
        }

        amount, suffix = (int(delay[:-1]), delay[-1]) if delay[-1] in suffixes else (int(delay), 'h')
        return timedelta(**{suffixes[suffix]: amount})

    def language(self) -> LanguageConfig:
        language = self._settings.get(
            'language', 
            self._env.str(
                'LANGUAGE', 
                DEFAULT_LANGUAGE
            )
        )

        return LanguageConfig(
            language=language
        )

    def logging(self) -> LoggingConfig:
        level_name = self._settings.get('log_level', DEFAULT_LOG_LEVEL)
        mapping = logging.getLevelNamesMapping()
        level = mapping.get(level_name.upper())

        level = self._env.log_level('LOG_LEVEL', level)

        is_gunicorn = os.environ.get('SERVER_SOFTWARE', '').startswith('gunicorn')

        return LoggingConfig(
            level=level,
            is_gunicorn=is_gunicorn
        )

    def admin(self) -> AdminConfig:
        admin: dict = self._settings.get('admin', {})

        with self._env.prefixed('ADMIN_'):
            username = admin.get(
                'username', 
                self._env.str(
                    'USERNAME',
                    DEFAULT_ADMIN_USERNAME
                )
            )

            password_hash = admin.get(
                'password_hash', 
                self._hashpw(self._env.str(
                    'PASSWORD', 
                    DEFAULT_ADMIN_PASSWORD
                ))
            )

            max_login_attempts = admin.get(
                'max_login_attempts', 
                self._env.int(
                    'MAX_LOGIN_ATTEMPTS',
                    DEFAULT_ADMIN_ATTEMPTS
                )
            )

            lockout_time = admin.get(
                'lockout_time', 
                self._env.int(
                    'LOCKOUT_TIME',
                    DEFAULT_ADMIN_LOCKOUT
                )
            )

        return AdminConfig(
            username=username,
            password_hash=password_hash,
            max_login_attempts=max_login_attempts,
            lockout_time=timedelta(seconds=lockout_time),
        )
    
    def radius(self) -> RadiusConfig:
        env = Env(prefix='RADIUS_')
        env.read_env()

        radius: dict = self._settings.get('radius', {})
        ports: dict = radius.get('ports', {})
        raw_hosts: dict = radius.get('hosts', {})

        enabled = env.bool('ENABLED', DEFAULT_RADIUS_ENABLED)
        addresses = radius.get('addresses', env.list('ADDRESSES', DEFAULT_RADIUS_ADDRESSES))
        auth_port = ports.get('auth', env.int('AUTH_PORT', DEFAULT_RADIUS_AUTH_PORT))
        acct_port = ports.get('acct', env.int('ACCT_PORT', DEFAULT_RADIUS_ACCT_PORT))
        coa_port = ports.get('coa', env.int('COA_PORT', DEFAULT_RADIUS_COA_PORT))

        ports = RadiusPortsConfig(
            auth=auth_port,
            acct=acct_port,
            coa=coa_port
        )
        
        hosts = {}
        for host, parametres in raw_hosts.items():
            parametres['secret'] = parametres.get('secret').encode()
            hosts[host] = server.RemoteHost(**parametres)

        return RadiusConfig(
            enabled=enabled,
            addresses=addresses, 
            ports=ports,
            hosts=hosts
        )

    def hotspot(self) -> HotspotConfig:
        hotspot: dict = self._settings.get('hotspot', {})

        online_timeout = hotspot.get('online_timeout', self._env.str('ONLINE_TIMEOUT', DEFAULT_ONLINE_TIMEOUT))

        with self._env.prefixed('USERS_'):
            with self._env.prefixed('STAFF_'):
                staff: dict = hotspot.get('staff', {})
                staff_user = HotspotUserConfig(
                    password=staff.get('password', self._env.str('PASS', DEFAULT_STAFF_PASSWORD)), 
                    delay=self._convert_delay(staff.get('delay', self._env.str('DELAY', DEFAULT_STAFF_DELAY)))
                )

            with self._env.prefixed('GUEST_'):
                guest: dict = hotspot.get('guest', {})
                guest_user = HotspotUserConfig(
                    password=guest.get('password', self._env.str('PASS', DEFAULT_GUEST_PASSWORD)), 
                    delay=self._convert_delay(guest.get('delay', self._env.str('DELAY', DEFAULT_GUEST_DELAY)))
                )

        return HotspotConfig(
            online_timeout=timedelta(seconds=online_timeout),
            staff=staff_user,
            guest=guest_user
        )

    def sender(self) -> SenderConfig:
        sender: dict = self._settings.get('radius', {})
        type = sender.get('type', self._env.str('TYPE', DEFAULT_SENDER_TYPE)).lower()

        with self._env.prefixed(f'{type.upper()}_'):
            url = sender.get('url', self._env.url('URL', None))
            api_key = sender.get('api_key', self._env.str('APIKEY', None))

        return SenderConfig(
            type=type,
            url=url,
            api_key=api_key
        )
    
    def load(self) -> Config:
        return Config(
            language=self.language(),
            logging=self.logging(),
            hotspot=self.hotspot(),
            sender=self.sender(),
            admin=self.admin(),
            radius=self.radius(),
            version=self._version
        )
