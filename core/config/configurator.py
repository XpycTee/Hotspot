from datetime import timedelta
from typing import List
from environs import Env

from core.config.defaults import *

from core.config.models import AdminConfig, AppConfig, LanguageConfig
from core.config.models.hotspot import HotspotConfig, HotspotUserConfig
from core.config.models.radius import RadiusConfig, RadiusPortsConfig, RemoteHost
from core.config.models.verificators import CallcheckConfig, SenderConfig, VProviderField, VProvidersList, VerificationMethod, VerificationProvider, VProviderType


class Configurator:
    def __init__(self, settings: dict | None = None, version: int | None = None):
        self._settings = settings or {}
        self.version = version or self._settings.get('version', 1)
        self._env = Env(prefix='HOTSPOT_')
        self._env.read_env()

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
        with self._env.prefixed('SENDER_'):
            type = sender.get('type', self._env.str('TYPE', DEFAULT_SENDER_TYPE)).lower()

            with self._env.prefixed(f'{type.upper()}_'):
                url = sender.get('url', self._env.url('URL', None))
                api_key = sender.get('api_key', self._env.str('APIKEY', None))

        return SenderConfig(
            type=type,
            url=url,
            api_key=api_key,
        )
    
    def _callcheck(self) -> CallcheckConfig:
        sender: dict = self._settings.get('callcheck', {})
        with self._env.prefixed('CALLCHECK_'):
            type = sender.get('type', self._env.str('TYPE', DEFAULT_CALLCHECK_TYPE)).lower()
            with self._env.prefixed(f'{type.upper()}_'):
                call_phone = sender.get('call_phone', self._env.url('CALLPHONE', None))
                api_key = sender.get('api_key', self._env.str('APIKEY', None))

        return CallcheckConfig(
            type=type,
            call_phone=call_phone,
            api_key=api_key,
        )
    
    def _verificators(self) -> List[VerificationProvider]:
        cfg: dict = self._settings.get('verificators', {})
        items = cfg.get('items', [])
        verificators = []
        
        for v in items:
            fields = v.get('fields')
            methods = v.get('supported_methods')
            p = VerificationProvider(
                type=v.get('type'),
                name=v.get('name'),
                enabled=v.get('enabled'),
                fields=[VProviderField(**f) for f in fields],
                supported_methods=[VerificationMethod(m) for m in methods]
            )
            verificators.append(p)

        if len(verificators) == 0:
            order = [
                VProviderType.SMSRU,
                VProviderType.ASTERISK,
                VProviderType.MIKROTIK,
                VProviderType.HUAWEI,
                # Always last
                VProviderType.DEBUG,
            ]
            verificators = [
                VerificationProvider(
                    type=VProviderType.SMSRU,
                    name='sms.ru',
                    enabled=False,
                    fields=[
                        VProviderField(),
                    ],
                    supported_methods=[
                        VerificationMethod.CALL,
                        VerificationMethod.CODE,
                    ],
                ),
                VerificationProvider(
                    type=VProviderType.ASTERISK,
                    name='Asterisk',
                    enabled=False,
                    fields=[
                        VProviderField(
                            name="call_phone",
                            label="Call phone",
                            type="text",
                        ),
                        VProviderField(
                            name="api_key",
                            label="API Key",
                            type="password",
                        ),
                    ],
                    supported_methods=[
                        VerificationMethod.CALL,
                    ],
                ),
                VerificationProvider(
                    type=VProviderType.MIKROTIK,
                    name='Mikrotik',
                    enabled=False,
                    fields=[
                        VProviderField(
                            name="url",
                            label="URL",
                            type="text",
                        ),
                    ],
                    supported_methods=[
                        VerificationMethod.CODE,
                    ],
                ),
                VerificationProvider(
                    type=VProviderType.HUAWEI,
                    name='Huawei',
                    enabled=False,
                    fields=[
                        VProviderField(
                            name="url",
                            label="URL",
                            type="text",
                        ),
                    ],
                    supported_methods=[
                        VerificationMethod.CODE,
                    ],
                ),
                VerificationProvider(
                    type=VProviderType.DEBUG,
                    name='Debug',
                    enabled=True,
                    fields=[],
                    supported_methods=[
                        VerificationMethod.CODE,
                    ],
                ),
            ]
        else:
            order = [VProviderType(t) for t in cfg.get('order')]

        return VProvidersList(
            items=verificators,
            order=order
        )

    def create(self) -> AppConfig:
        return AppConfig(
            language=self._language(),
            hotspot=self._hotspot(),
            verificators=self._verificators(),
            admin=self._admin(),
            radius=self._radius(),
            version=self.version,
        )
