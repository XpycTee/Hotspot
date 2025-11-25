#core/wifi/auth.py

import datetime
import logging

from core.user.repository import check_blacklist
from core.user.repository import update_status
from core.user.repository import check_employee
from core.user.expiration import update_expiration
from core.utils.phone import normalize_phone
from core.wifi.repository import find_by_fp
from core.wifi.fingerprint import get_fingerprint
from core.wifi.repository import find_by_mac
from core.db.session import get_session


def authenticate_by_mac(mac, hardware_fp=None):
    resp = {"status": "NOT_FOUND"}
    now_time = datetime.datetime.now()
    wifi_client = find_by_mac(mac)
    if wifi_client:
        expiration = wifi_client.get('expiration')
        if now_time > expiration:
            resp = {"status": "EXPIRED"}
            logging.info(f"{mac} is exired")
            return resp

        phone_number = wifi_client.get('phone')
        if not phone_number:
            logging.warning(f"{mac}'s phone not found")
            return resp
        
        if check_blacklist(phone_number):
            resp = {"status": "BLOCKED"}
            logging.info(f"{mac} is blocked")
            return resp

        is_employee = wifi_client.get('employee')
        if check_employee(phone_number) == is_employee:
            user_fp = get_fingerprint(phone_number, hardware_fp)
            logging.info(f"{mac} authing by expiration")
            db_mac = wifi_client.get('mac')
            resp = {
                "status": "OK", 
                "phone": phone_number, 
                "mac": db_mac, 
                "user_fp": user_fp, 
                "employee": is_employee
            }
            return resp
        
    return resp


def authenticate_by_phone(mac, phone_number, hardware_fp=None):
    resp = {"status": "NOT_FOUND"}

    phone_number = normalize_phone(phone_number)

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


    if wifi_client and (phone:= wifi_client.get('phone')) and phone == phone_number:
        is_employee = check_employee(phone_number)

        #users_config = current_app.config['HOTSPOT_USERS']
        #hotspot_user = users_config['employee'] if is_employee else users_config['guest']
        #hotspot_user.get('delay')
        # TODO Refactor getting delay
        delay = datetime.timedelta(days = 1)
        db_mac = wifi_client.get('mac')
        update_expiration(db_mac, delay)
        update_status(db_mac, is_employee)

        logging.info(f"{mac} authing by {auth_method}")
        resp = {
            "status": "OK", 
            "phone": phone_number, 
            "mac": db_mac, 
            "user_fp": user_fp, 
            "employee": is_employee
        }
        return resp
    
    return resp
