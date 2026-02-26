from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from core.hotspot.user.blacklist import check_blacklist
from core.hotspot.user.expiration import update_expiration
from core.hotspot.wifi.fingerprint import hash_fingerprint
from core.hotspot.wifi.repository import create_wifi_client, find_by_fp, find_by_mac, update_mac
from core.logging import get_logger

logger = get_logger('core.hotspot.authorization.service')


class AuthStatus(Enum):
    AUTHORIZED = auto()
    FAILED = auto()
    BLOCKED = auto()


@dataclass
class AuthResponse:
    status: AuthStatus

    # Options
    mac: str | None = None
    phone: str | None = None
    user_fp: str | None = None
    is_employee: bool | None = None
    error_message: str | None = None


class Authorization:
    def authorized(self, user_fp):
        if not user_fp:
            return False

        now_time = datetime.now()
        wifi_client = find_by_fp(user_fp)
        if wifi_client and now_time < wifi_client.get('expiration'):
            return True
        return False
        
    def mac_authorization(self, mac: str, hardware_fp: str) -> AuthResponse:
        now_time = datetime.now()
        wifi_client = find_by_mac(mac)
        if wifi_client:
            if now_time > wifi_client.get('expiration'):
                msg = f"{mac} is exired"
                logger.info(msg)
                return AuthResponse(
                    status=AuthStatus.FAILED,
                    error_message=msg,
                )

            phone = wifi_client.get('phone')
            if not phone:
                logger.warning(f"{mac}'s phone not found")
                return AuthResponse(
                    status=AuthStatus.FAILED,
                    error_message="User's phone not found",
                )
            
            if check_blacklist(phone):
                logger.info(f"{mac} is blocked")
                return AuthResponse(
                    status=AuthStatus.BLOCKED,
                )

            user_fp = hash_fingerprint(phone, hardware_fp)
            logger.info(f"{mac} authing by expiration")
            return AuthResponse(
                status=AuthStatus.AUTHORIZED,
                mac=wifi_client.get('mac'),
                phone=phone,
                user_fp=user_fp,
                is_employee=wifi_client.get('is_employee'),
            )
        return AuthResponse(
            status=AuthStatus.FAILED,
        )

    def phone_authorization(self, mac: str, phone: str, hardware_fp: str) -> AuthResponse:
        if check_blacklist(phone):
            logger.info(f"{mac} is blocked")
            return AuthResponse(
                status=AuthStatus.BLOCKED,
            )

        use_fp = False
        wifi_client = find_by_mac(mac)
        
        user_fp = hash_fingerprint(phone, hardware_fp)

        if not wifi_client and user_fp:
            wifi_client = find_by_fp(user_fp)
            use_fp = True

        if wifi_client and (db_phone:= wifi_client.get('phone')) and db_phone == phone:
            wifi_client_mac = wifi_client.get('mac')

            update_expiration(wifi_client_mac)
            
            if user_fp:
                update_mac(wifi_client_mac, mac)

            logger.info(f"{mac} authing by {'phone & fp' if use_fp else 'phone & mac'}")
            return AuthResponse(
                status=AuthStatus.AUTHORIZED,
                phone=phone,
                user_fp=user_fp,
            )
        return AuthResponse(
            status=AuthStatus.FAILED,
            phone=phone,
            user_fp=user_fp,
            error_message="User not found",
        )

    def authorization(self, mac: str, phone: str, user_fp: str) -> AuthResponse:
        if check_blacklist(phone):
            logger.info(f"{mac} is blocked")
            return AuthResponse(
                status=AuthStatus.BLOCKED,
            )

        use_fp = False
        wifi_client = find_by_mac(mac)
        
        if not wifi_client:
            wifi_client = find_by_fp(user_fp)
            use_fp = True

        if wifi_client and (db_phone:= wifi_client.get('phone')) and db_phone == phone:
            wifi_client_mac = wifi_client.get('mac')

            update_expiration(wifi_client_mac)
            
            if use_fp:
                update_mac(wifi_client_mac, mac)

            logger.info(f"{mac} authing by {'phone & fp' if use_fp else 'phone & mac'}")
            return AuthResponse(
                status=AuthStatus.AUTHORIZED,
                phone=phone,
                user_fp=user_fp,
            )
        
        create_wifi_client(mac, phone, user_fp)
        return AuthResponse(
            status=AuthStatus.AUTHORIZED,
            phone=phone,
            user_fp=user_fp,
        )
