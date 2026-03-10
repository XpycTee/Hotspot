from core.config import get_config
from core.hotspot.user.token import generate_token, generate_trial_token
from core.hotspot.user.repository import update_clients_numbers_last_seen
from core.hotspot.user.employees import check_employee
from core.logging import get_logger
from core.hotspot.wifi.challange import hash_chap
from core.hotspot.wifi.fingerprint import update_fingerprint


logger = get_logger('core.hotspot.wifi.auth')


def get_credentials(mac, phone_number, user_fp=None, chap_id=None, chap_challenge=None):
    config = get_config()
    if config.radius.enabled:
        username = mac
        password = generate_token(mac)
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


def get_trial_credentials(mac, chap_id=None, chap_challenge=None):
    password = generate_trial_token(mac)

    if chap_id and chap_challenge:
        password = hash_chap(chap_id, password, chap_challenge)

    return {
        "username": mac,
        "password": password,
    }
