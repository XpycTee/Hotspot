import datetime

from core.config import get_config
from core.config.response_code import BLOCKED, EXPIRED, NOT_FOUND, OK
from core.hotspot.user.blacklist import check_blacklist
from core.hotspot.user.token import generate_token
from core.hotspot.auth.code import clear_code, increment_attempts, verify_code
from core.hotspot.auth.confirm import auth_confirm
from core.hotspot.user.repository import update_clients_numbers_last_seen
from core.hotspot.user.employees import check_employee
from core.hotspot.user.expiration import update_expiration
from core.logging import get_logger
from core.utils.language import get_translate
from core.utils.phone import normalize_phone
from core.hotspot.wifi.challange import hash_chap
from core.hotspot.wifi.repository import create_or_udpate_wifi_client, find_by_fp, update_mac
from core.hotspot.wifi.fingerprint import hash_fingerprint, update_fingerprint
from core.hotspot.wifi.repository import find_by_mac


logger = get_logger('core.hotspot.wifi.auth')


def authenticate_by_mac(mac, hardware_fp=None):
    now_time = datetime.datetime.now()
    wifi_client = find_by_mac(mac)
    if wifi_client:
        if now_time > wifi_client.get('expiration'):
            logger.info(f"{mac} is exired")
            return EXPIRED

        phone_number = wifi_client.get('phone')
        if not phone_number:
            logger.warning(f"{mac}'s phone not found")
            return NOT_FOUND
        
        if check_blacklist(phone_number):
            logger.info(f"{mac} is blocked")
            return BLOCKED

        user_fp = hash_fingerprint(phone_number, hardware_fp)
        auth_confirm(user_fp)
        logger.info(f"{mac} authing by expiration")
        response = {
            "status": "OK", 
            "phone": phone_number, 
            "mac": wifi_client.get('mac'), 
            "user_fp": user_fp, 
            "is_employee": wifi_client.get('is_employee')
        }
        return response
    return NOT_FOUND


def authenticate_by_phone(mac, phone_number, hardware_fp):
    phone_number = normalize_phone(phone_number)

    if check_blacklist(phone_number):
        logger.info(f"{mac} is blocked")
        return BLOCKED

    use_fp = False
    wifi_client = find_by_mac(mac)
    
    user_fp = hash_fingerprint(phone_number, hardware_fp)

    if not wifi_client and user_fp:
        wifi_client = find_by_fp(user_fp)
        use_fp = True

    if wifi_client and (phone:= wifi_client.get('phone')) and phone == phone_number:
        wifi_client_mac = wifi_client.get('mac')

        update_expiration(wifi_client_mac)
        
        if user_fp:
            update_mac(wifi_client_mac, mac)

        auth_confirm(user_fp)
        logger.info(f"{mac} authing by {'phone & fp' if use_fp else 'phone & mac'}")
        response = {
            "status": "OK", 
            "phone": phone_number, 
            "user_fp": user_fp
        }
        return response
    return NOT_FOUND


def authenticate_by_code(user_fp, mac, code, phone_number):
    if verify:=verify_code(user_fp, code):
        create_or_udpate_wifi_client(mac, phone_number)
        clear_code(user_fp)
        logger.debug("Auth by code")
        auth_confirm(user_fp)
        return OK
    elif verify is None:
        return {"status": "CODE_EXPIRED", 'error_message': get_translate('errors.auth.expired_code')}

    attempts = increment_attempts(user_fp)
    if attempts < 3:
        return {"status": "BAD_TRY", 'error_message': get_translate('errors.auth.bad_code_try')}

    clear_code(user_fp)
    return {"status": "BAD_CODE", 'error_message': get_translate('errors.auth.bad_code_all')}


def get_credentials(mac, phone_number, user_fp=None, chap_id=None, chap_challenge=None):
    config = get_config()
    if config.radius.enabled:
        username = phone_number
        password = generate_token(phone_number)
    else:
        if check_employee(phone_number):
            username = 'employee'
            password = config.hotspot.staff.password
        else:
            username = 'guest'
            password = config.hotspot.guest.password

    if chap_id and chap_challenge:
        password = hash_chap(chap_id, password, chap_challenge)

    if user_fp:
        update_fingerprint(mac, user_fp)

    update_clients_numbers_last_seen(phone_number)

    return {
        "username": username,
        "password": password
    }
