#core/wifi/auth.py

import datetime
import logging

from core.user.blacklist import check_blacklist
from core.user.employee import check_employee, update_status
from core.user.expiration import update_expiration
from core.wifi.client import find_by_fp, find_by_mac
from core.wifi.fingerprint import get_fingerprint


def authenticate_by_mac(mac, hardware_fp=None):
    resp = {"status": "NOT_FOUND"}
    now_time = datetime.datetime.now()
    wifi_client = find_by_mac(mac)
    if wifi_client:
        if now_time > wifi_client.expiration:
            resp = {"status": "EXPIRED"}
            logging.info(f"{mac} is exired")
            return resp
        
        phone = wifi_client.phone
        if not phone:
            logging.warning(f"{mac}'s phone not found")
            return resp
        
        phone_number = phone.phone_number
        if check_blacklist(phone_number):
            resp = {"status": "BLOCKED"}
            logging.info(f"{mac} is blocked")
            return resp

        if check_employee(phone_number) == wifi_client.employee:
            user_fp = get_fingerprint(phone_number, hardware_fp)
            logging.info(f"{mac} authing by expiration")
            resp = {"status": "OK", "phone": phone_number, "user_fp": user_fp, "employee": wifi_client.employee}
            return resp
        
    return resp


def authenticate_by_phone(mac, phone_number, hardware_fp=None):
    resp = {"status": "NOT_FOUND"}

    if check_blacklist(phone_number):
        resp = {"status": "BLOCKED"}
        logging.info(f"{mac} is blocked")
        return resp

    auth_method = "phone & mac"
    wifi_client = find_by_mac(mac)
    
    user_fp = get_fingerprint(phone_number, hardware_fp)

    if not wifi_client and user_fp:
        wifi_client = find_by_fp(user_fp)
        auth_method = "phone & fp"

    phone = wifi_client.phone
    if not phone:
        logging.warning(f"{mac}'s phone not found")
        return resp

    if wifi_client and phone.phone_number == phone_number:
        is_employee = check_employee(phone_number)

        #users_config = current_app.config['HOTSPOT_USERS']
        #hotspot_user = users_config['employee'] if is_employee else users_config['guest']
        #hotspot_user.get('delay')
        delay = datetime.timedelta(days = 1) # TODO Refactor getting delay

        update_expiration(wifi_client, delay)
        update_status(wifi_client, is_employee)

        logging.info(f"{mac} authing by {auth_method}")
        resp = {"status": "OK", "phone": phone_number, "user_fp": user_fp, "employee": is_employee}
        return resp
    
    return resp
