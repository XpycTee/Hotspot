import datetime
import secrets

from core.hotspot.user.blacklist import check_blacklist
from core.logging.logger import logger
from core.config.radius import RADIUS_ENABLED
from core.config.users import GUEST_USER, STAFF_USER
from core.cache import get_cache
from core.hotspot.sms.code import clear_code, increment_attempts, verify_code
from core.hotspot.user.repository import update_clients_numbers_last_seen
from core.hotspot.user.employees import update_employee_status
from core.hotspot.user.employees import check_employee
from core.hotspot.user.expiration import update_expiration
from core.utils.language import get_translate
from core.utils.phone import normalize_phone
from core.hotspot.wifi.challange import hash_chap
from core.hotspot.wifi.repository import create_or_udpate_wifi_client, find_by_fp
from core.hotspot.wifi.fingerprint import hash_fingerprint, update_fingerprint
from core.hotspot.wifi.repository import find_by_mac



def authenticate_by_mac(mac, hardware_fp=None):
    now_time = datetime.datetime.now()
    wifi_client = find_by_mac(mac)
    if wifi_client:
        if now_time > wifi_client.get('expiration'):
            logger.info(f"{mac} is exired")
            return {"status": "EXPIRED"}

        phone_number = wifi_client.get('phone')
        if not phone_number:
            logger.warning(f"{mac}'s phone not found")
            return {"status": "NOT_FOUND"}
        
        if check_blacklist(phone_number):
            logger.info(f"{mac} is blocked")
            return {"status": "BLOCKED"}

        is_employee = check_employee(phone_number)
        if wifi_client.get('employee') == is_employee:
            user_fp = hash_fingerprint(phone_number, hardware_fp)
            logger.info(f"{mac} authing by expiration")
            response = {
                "status": "OK", 
                "phone": phone_number, 
                "mac": wifi_client.get('mac'), 
                "user_fp": user_fp, 
                "employee": is_employee
            }
            return response
    return {"status": "NOT_FOUND"}


def authenticate_by_phone(mac, phone_number, hardware_fp=None):
    phone_number = normalize_phone(phone_number)

    if check_blacklist(phone_number):
        logger.info(f"{mac} is blocked")
        return {"status": "BLOCKED"}

    auth_method = "phone & mac"
    wifi_client = find_by_mac(mac)
    
    user_fp = hash_fingerprint(phone_number, hardware_fp)

    if not wifi_client and user_fp:
        wifi_client = find_by_fp(user_fp)
        auth_method = "phone & fp"

    if wifi_client and (phone:= wifi_client.get('phone')) and phone == phone_number:
        is_employee = check_employee(phone_number)

        wifi_client_mac = wifi_client.get('mac')

        if wifi_client.get('employee') != is_employee:
            update_employee_status(wifi_client_mac, is_employee)

        update_expiration(wifi_client_mac)

        logger.info(f"{mac} authing by {auth_method}")
        response = {
            "status": "OK", 
            "phone": phone_number, 
            "mac": wifi_client_mac, 
            "user_fp": user_fp, 
            "employee": is_employee
        }
        return response
    return {"status": "NOT_FOUND"}


def authenticate_by_code(session_id, mac, code, phone_number):
    if verify:=verify_code(session_id, code):
        is_employee = check_employee(phone_number)
        create_or_udpate_wifi_client(mac, is_employee, phone_number)
        clear_code(session_id)
        logger.debug("Auth by code")
        return {"status": "OK"}
    elif verify is None:
        return {"status": "CODE_EXPIRED", 'error_message': get_translate('errors.auth.expired_code')}

    attempts = increment_attempts(session_id)
    if attempts < 3:
        return {"status": "BAD_TRY", 'error_message': get_translate('errors.auth.bad_code_try')}

    clear_code(session_id)
    return {"status": "BAD_CODE", 'error_message': get_translate('errors.auth.bad_code_all')}


def get_credentials(mac, phone_number, user_fp=None, chap_id=None, chap_challenge=None):
    if RADIUS_ENABLED:
        cache = get_cache()
        username = phone_number
        password = secrets.token_hex(32)
        cache.set(f"auth:token:{phone_number}", password)
    else:
        is_employee = check_employee(phone_number)
        username = 'employee' if is_employee else 'guest'
        if is_employee:
            password = STAFF_USER.get('password')
        else:
            password = GUEST_USER.get('password')

    if chap_id and chap_challenge:
        password = hash_chap(chap_id, password, chap_challenge)

    if user_fp:
        update_fingerprint(mac, user_fp)

    update_clients_numbers_last_seen(phone_number)

    return {
        "username": username,
        "password": password
    }
