from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any

from core.hotspot.user.blacklist import check_blacklist
from core.hotspot.wifi.fingerprint import hash_fingerprint
from core.hotspot.wifi.repository import create_wifi_client, find_by_fp, find_by_mac, update_mac, update_wifi_client
from core.logging import get_logger
from core.utils.language import get_translate

logger = get_logger('core.hotspot.authorization.service')


class AuthStatus(Enum):
    AUTHORIZED = auto()
    FAILED = auto()
    BLOCKED = auto()


class AuthFailReason(Enum):
    NOT_FOUND = auto()
    EXPIRED = auto()
    PHONE_MISSING = auto()
    USER_FP_MISSING = auto()


@dataclass
class AuthResponse:
    status: AuthStatus

    # Options
    mac: str | None = None
    phone: str | None = None
    user_fp: str | None = None
    is_employee: bool | None = None
    error_message: str | None = None
    fail_reason: AuthFailReason | None = None


class Authorization:
    def _mask_mac(self, mac: str | None) -> str | None:
        if not mac:
            return None
        parts = mac.split(':')
        if len(parts) < 6:
            return 'XX:XX:XX'
        return 'XX:XX:XX:' + ':'.join(parts[3:])

    def _ctx(self, flow_ctx: dict[str, Any] | None, event: str, **kwargs: Any) -> dict[str, Any]:
        ctx: dict[str, Any] = dict(flow_ctx or {})
        ctx['event'] = event
        for key, value in kwargs.items():
            if value is not None:
                ctx[key] = value
        return ctx

    def _prefix(self, ctx: dict[str, Any]) -> str:
        auth_flow = ctx.get('auth_flow_id') or '-'
        verify_flow = ctx.get('verify_session_id') or '-'
        stage = ctx.get('stage') or '-'
        return f'[auth_flow={auth_flow} verify={verify_flow} stage={stage}]'

    def _log(self, level: str, message: str, flow_ctx: dict[str, Any] | None, event: str, **kwargs: Any):
        ctx = self._ctx(flow_ctx, event, **kwargs)
        log_fn = getattr(logger, level)
        log_fn(f'{self._prefix(ctx)} {message}', extra=ctx)

    def authorized(self, user_fp):
        if not user_fp:
            return False

        now_time = datetime.now()
        wifi_client = find_by_fp(user_fp)
        if wifi_client and now_time < wifi_client.get('expiration'):
            return True
        return False

    def mac_authorization(self, mac: str, flow_ctx: dict[str, Any] | None = None) -> AuthResponse:
        now_time = datetime.now()

        wifi_client = find_by_mac(mac)

        if not wifi_client:
            self._log('info', 'MAC authorization: client not found', flow_ctx, 'auth.mac.check', status='FAILED', fail_reason=AuthFailReason.NOT_FOUND.name, mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.FAILED,
                error_message=get_translate('errors.hotspot.auth.not_found'),
                fail_reason=AuthFailReason.NOT_FOUND,
            )

        if now_time > wifi_client.get('expiration'):
            self._log('info', 'MAC authorization: record expired', flow_ctx, 'auth.mac.check', status='FAILED', fail_reason=AuthFailReason.EXPIRED.name, mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.FAILED,
                error_message=get_translate('errors.hotspot.auth.expired'),
                fail_reason=AuthFailReason.EXPIRED,
            )

        phone = wifi_client.get('phone')
        if not phone:
            self._log('warning', 'MAC authorization: phone missing', flow_ctx, 'auth.mac.check', status='FAILED', fail_reason=AuthFailReason.PHONE_MISSING.name, mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.FAILED,
                error_message=get_translate('errors.hotspot.auth.phone_missing'),
                fail_reason=AuthFailReason.PHONE_MISSING,
            )

        if check_blacklist(phone):
            self._log('warning', 'MAC authorization: phone blocked', flow_ctx, 'auth.mac.check', status='BLOCKED', fail_reason='BLOCKED', mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.BLOCKED,
                error_message=get_translate('errors.hotspot.auth.blocked'),
            )

        user_fp = wifi_client.get('user_fp')
        if not user_fp:
            self._log('warning', 'MAC authorization: user_fp missing', flow_ctx, 'auth.mac.check', status='FAILED', fail_reason=AuthFailReason.USER_FP_MISSING.name, mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.FAILED,
                error_message=get_translate('errors.hotspot.auth.user_fp_missing'),
                fail_reason=AuthFailReason.USER_FP_MISSING,
            )

        self._log('info', 'MAC authorization: success by expiration window', flow_ctx, 'auth.mac.check', status='AUTHORIZED', mac=self._mask_mac(mac))
        return AuthResponse(
            status=AuthStatus.AUTHORIZED,
            mac=wifi_client.get('mac'),
            phone=phone,
            user_fp=user_fp,
            is_employee=wifi_client.get('is_employee'),
        )

    def phone_authorization(self, mac: str, phone: str, hardware_fp: str, flow_ctx: dict[str, Any] | None = None) -> AuthResponse:
        if check_blacklist(phone):
            self._log('warning', 'Phone authorization: phone blocked', flow_ctx, 'auth.phone.check', status='BLOCKED', fail_reason='BLOCKED', mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.BLOCKED,
            )

        use_fp = False
        wifi_client = find_by_mac(mac)

        user_fp = hash_fingerprint(phone, hardware_fp)

        if not wifi_client and user_fp:
            wifi_client = find_by_fp(user_fp)
            use_fp = True

        if wifi_client and (db_phone := wifi_client.get('phone')) and db_phone == phone:
            wifi_client_mac = wifi_client.get('mac')

            # Persist refreshed fingerprint so sendin authorization by user_fp stays consistent.
            update_wifi_client(wifi_client_mac, phone, user_fp)

            if use_fp:
                update_mac(wifi_client_mac, mac)

            self._log('info', 'Phone authorization: success', flow_ctx, 'auth.phone.check', status='AUTHORIZED', auth_mode='phone_fp' if use_fp else 'phone_mac', mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.AUTHORIZED,
                phone=phone,
                user_fp=user_fp,
            )

        self._log('info', 'Phone authorization: client not found', flow_ctx, 'auth.phone.check', status='FAILED', fail_reason=AuthFailReason.NOT_FOUND.name, mac=self._mask_mac(mac))
        return AuthResponse(
            status=AuthStatus.FAILED,
            error_message=get_translate('errors.hotspot.auth.not_found'),
            fail_reason=AuthFailReason.NOT_FOUND,
        )

    def authorization(self, mac: str, phone: str, hardware_fp: str, flow_ctx: dict[str, Any] | None = None) -> AuthResponse:
        if check_blacklist(phone):
            self._log('warning', 'Final authorization: phone blocked', flow_ctx, 'auth.finalize', status='BLOCKED', fail_reason='BLOCKED', mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.BLOCKED,
            )

        use_fp = False
        wifi_client = find_by_mac(mac)

        user_fp = hash_fingerprint(phone, hardware_fp)

        if not wifi_client:
            wifi_client = find_by_fp(user_fp)
            use_fp = True

        if not wifi_client:
            create_wifi_client(mac, phone, user_fp)
            self._log('info', 'Final authorization: created new wifi client', flow_ctx, 'auth.finalize', status='AUTHORIZED', auth_mode='create', mac=self._mask_mac(mac))
            return AuthResponse(
                status=AuthStatus.AUTHORIZED,
                user_fp=user_fp,
            )

        wifi_client_mac = wifi_client.get('mac')
        update_wifi_client(wifi_client_mac, phone, user_fp)

        if use_fp:
            update_mac(wifi_client_mac, mac)

        self._log('info', 'Final authorization: updated existing wifi client', flow_ctx, 'auth.finalize', status='AUTHORIZED', auth_mode='phone_fp' if use_fp else 'phone_mac', mac=self._mask_mac(mac))
        return AuthResponse(
            status=AuthStatus.AUTHORIZED,
            user_fp=user_fp,
        )
