from datetime import timedelta
import logging
import os
import bcrypt
from environs import Env

from pyrad2 import server

from core.config.models import (
    AdminConfig,
    DatabaseConfig,
    HotspotConfig,
    HotspotUserConfig,
    LanguageConfig,
    LoggingConfig, 
    RadiusConfig, 
    RadiusPortsConfig,
    RedisConfig,
    SenderConfig
)

from core.config.defaults import (
    DEFAULT_LANGUAGE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_DB_URL,
    DEFAULT_REDIS_URL,
    DEFAULT_ONLINE_TIMEOUT,
    DEFAULT_AUTH_PORT,
    DEFAULT_ACCT_PORT,
    DEFAULT_COA_PORT,
)


class ConfigLoader:
    def __init__(self, settings: dict | None):
        self._settings = settings or {}

        self._env = Env(prefix='HOTSPOT_')
        self._env.read_env()

        self._r_env = Env(prefix='RADIUS_')
        self._r_env.read_env()

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
        language = self._env.str(
            'LANGUAGE', 
            self._settings.get('language', DEFAULT_LANGUAGE)
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

    def db(self) -> DatabaseConfig:
        with self._env.prefixed('DB_'):
            url = self._env.str(
                'URL',
                self._settings.get('db_url', DEFAULT_DB_URL),
            )

        return DatabaseConfig(url=url)

    def redis(self) -> RedisConfig:
        with self._env.prefixed('REDIS_'):
            url = self._env.str(
                'URL',
                self._settings.get('redis_url', DEFAULT_REDIS_URL),
            )

        return RedisConfig(url=url)

    def admin(self) -> AdminConfig:
        admin: dict = self._settings.get('admin', {})

        with self._env.prefixed('ADMIN_'):
            username = self._env.str(
                'USERNAME',
                admin.get('username', 'admin'),
            )

            password_hash = admin.get(
                'password_hash', 
                self._hashpw(self._env.str('PASSWORD', 'admin')),
            )

            max_login_attempts = self._env.int(
                'MAX_LOGIN_ATTEMPTS',
                admin.get('max_login_attempts', 3),
            )

            lockout_time = self._env.int(
                'LOCKOUT_TIME',
                admin.get('lockout_time', 5),
            )

        return AdminConfig(
            username=username,
            password_hash=password_hash,
            max_login_attempts=max_login_attempts,
            lockout_time=timedelta(minutes=lockout_time),
        )
    
    def radius(self) -> RadiusConfig:
        radius: dict = self._settings.get('radius', {})
        ports: dict = radius.get('ports', {})
        raw_hosts: dict = radius.get('hosts', {})

        enabled = self._r_env.bool('ENABLED', True)
        addresses = self._r_env.list('ADDRESSES', radius.get('addresses', ['0.0.0.0']))
        auth_port = self._r_env.int('AUTH_PORT', ports.get('auth', DEFAULT_AUTH_PORT))
        acct_port = self._r_env.int('ACCT_PORT', ports.get('acct', DEFAULT_ACCT_PORT))
        coa_port = self._r_env.int('COA_PORT', ports.get('CoA', DEFAULT_COA_PORT))

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
        users: dict = hotspot.get('users', {})

        online_timeout = self._env.str('ONLINE_TIMEOUT', hotspot.get('online_timeout', DEFAULT_ONLINE_TIMEOUT))

        with self._env.prefixed('USERS_'):
            with self._env.prefixed('STAFF_'):
                staff = users.get('staff', {})
                staff_user = HotspotUserConfig(
                    password=self._env.str('PASS', staff.get('password', 'supersecret')), 
                    delay=self._convert_delay(self._env.str('DELAY', staff.get('delay', '30d')))
                )

            with self._env.prefixed('GUEST_'):
                guest = users.get('guest', {})
                guest_user = HotspotUserConfig(
                    password=self._env.str('PASS', guest.get('password', 'secret')), 
                    delay=self._convert_delay(self._env.str('DELAY', guest.get('delay', '1d')))
                )

        return HotspotConfig(
            online_timeout=timedelta(seconds=online_timeout),
            staff=staff_user,
            guest=guest_user
        )

    def sender(self) -> SenderConfig:
        sender: dict = self._settings.get('radius', {})
        type = self._env.str('TYPE', sender.get('type', 'debug')).lower()

        with self._env.prefixed(f'{type.upper()}_'):
            url = self._env.url('URL', sender.get('url', None))
            api_key = self._env.str('APIKEY', sender.get('api_key', None))

        return SenderConfig(
            type=type,
            url=url,
            api_key=api_key
        )