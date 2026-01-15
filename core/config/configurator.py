from datetime import timedelta
import bcrypt
from environs import Env
from sqlalchemy import select

from core.config.models import *
from core.config.defaults import *
from core.database.models.admin_users import AdminUsers
from core.database.session import get_session


class Configurator:
    def __init__(self, settings: dict | None = None, version: int | None = None):
        self._settings = settings or {}
        self.version = version or self._settings.get('version', 1)
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

    def _language(self) -> LanguageConfig:
        language = self._settings.get('language', {})
        name = language.get(
            'name', 
            self._env.str(
                'LANGUAGE', 
                DEFAULT_LANGUAGE
            )
        )
        return LanguageConfig(
            name=name
        )

    def _admin(self) -> AdminConfig:
        admin: dict = self._settings.get('admin', {})

        with self._env.prefixed('ADMIN_'):
            with get_session() as db_session:
                username = self._env.str(
                        'USERNAME',
                        DEFAULT_ADMIN_USERNAME,
                    )
                
                query = select(AdminUsers).where(username==username)
                db_user = db_session.scalars(query).first()

                if not db_user:
                    password_hash = self._hashpw(self._env.str(
                        'PASSWORD', 
                        DEFAULT_ADMIN_PASSWORD,
                    ))
                    access = {
                        'hotspot': 'admin',
                        'radius': 'admin',
                        'sender': 'admin',
                        'users': 'admin',
                    }
                    new_user = AdminUsers(
                        username=username, 
                        password_hash=password_hash, 
                        access=access,
                    )
                    db_session.add(new_user)

            max_login_attempts = admin.get(
                'max_login_attempts', 
                self._env.int(
                    'MAX_LOGIN_ATTEMPTS',
                    DEFAULT_ADMIN_ATTEMPTS,
                )
            )

            lockout_time = admin.get(
                'lockout_time', 
                timedelta(seconds=self._env.int(
                    'LOCKOUT_TIME',
                    DEFAULT_ADMIN_LOCKOUT,
                ))
            )

        return AdminConfig(
            max_login_attempts=max_login_attempts,
            lockout_time=lockout_time,
        )
    
    def _radius(self) -> RadiusConfig:
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
            coa=coa_port,
        )
        
        hosts = {h: RemoteHost(**p) for h, p in raw_hosts.items()}

        return RadiusConfig(
            enabled=enabled,
            addresses=addresses, 
            ports=ports,
            hosts=hosts,
        )

    def _hotspot(self) -> HotspotConfig:
        hotspot: dict = self._settings.get('hotspot', {})

        online_timeout = hotspot.get('online_timeout', timedelta(seconds=self._env.int('ONLINE_TIMEOUT', DEFAULT_ONLINE_TIMEOUT)))

        with self._env.prefixed('USERS_'):
            with self._env.prefixed('STAFF_'):
                staff: dict = hotspot.get('staff', {})
                staff_user = HotspotUserConfig(
                    password=staff.get('password', self._env.str('PASS', DEFAULT_STAFF_PASSWORD)), 
                    delay=staff.get('delay', self._convert_delay(self._env.str('DELAY', DEFAULT_STAFF_DELAY))),
                )

            with self._env.prefixed('GUEST_'):
                guest: dict = hotspot.get('guest', {})
                guest_user = HotspotUserConfig(
                    password=guest.get('password', self._env.str('PASS', DEFAULT_GUEST_PASSWORD)), 
                    delay=guest.get('delay', self._convert_delay(self._env.str('DELAY', DEFAULT_GUEST_DELAY))),
                )

        return HotspotConfig(
            online_timeout=online_timeout,
            staff=staff_user,
            guest=guest_user,
        )

    def _sender(self) -> SenderConfig:
        sender: dict = self._settings.get('sender', {})
        type = sender.get('type', self._env.str('TYPE', DEFAULT_SENDER_TYPE)).lower()

        with self._env.prefixed(f'{type.upper()}_'):
            url = sender.get('url', self._env.url('URL', None))
            api_key = sender.get('api_key', self._env.str('APIKEY', None))

        return SenderConfig(
            type=type,
            url=url,
            api_key=api_key,
        )
    
    def create(self) -> AppConfig:
        return AppConfig(
            language=self._language(),
            hotspot=self._hotspot(),
            sender=self._sender(),
            admin=self._admin(),
            radius=self._radius(),
            version=self.version,
        )
