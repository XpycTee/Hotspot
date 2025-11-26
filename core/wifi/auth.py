import datetime
import logging

from core.sms.code import clear_code, increment_attempts, verify_code
from core.user.repository import check_blacklist
from core.user.repository import update_status
from core.user.repository import check_employee
from core.user.expiration import update_expiration
from core.utils.phone import normalize_phone
from core.wifi.repository import create_or_udpate_wifi_client, find_by_fp
from core.wifi.fingerprint import hash_fingerprint
from core.wifi.repository import find_by_mac



def authenticate_by_mac(mac, hardware_fp=None):
    now_time = datetime.datetime.now()
    wifi_client = find_by_mac(mac)
    if wifi_client:
        if now_time > wifi_client.get('expiration'):
            logging.info(f"{mac} is exired")
            return {"status": "EXPIRED"}

        phone_number = wifi_client.get('phone')
        if not phone_number:
            logging.warning(f"{mac}'s phone not found")
            return {"status": "NOT_FOUND"}
        
        if check_blacklist(phone_number):
            logging.info(f"{mac} is blocked")
            return {"status": "BLOCKED"}

        is_employee = check_employee(phone_number)
        if wifi_client.get('employee') == is_employee:
            user_fp = hash_fingerprint(phone_number, hardware_fp)
            logging.info(f"{mac} authing by expiration")
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
        logging.info(f"{mac} is blocked")
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
            update_status(wifi_client_mac, is_employee)

        update_expiration(wifi_client_mac)

        logging.info(f"{mac} authing by {auth_method}")
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
        logging.debug("Auth by code")
        return {"status": "OK"}
    elif verify is None:
        return {"status": "CODE_EXPIRED"}

    attempts = increment_attempts(session_id)
    if attempts < 3:
        return {"status": "BAD_TRY"}

    clear_code(session_id)
    return {"status": "BAD_CODE"}
