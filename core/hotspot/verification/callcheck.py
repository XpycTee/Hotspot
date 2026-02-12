from core.config.response_code import OK

from core.logging import get_logger
from core.config.verificators import get_callcheck


logger = get_logger('core.hotspot.verification.callcheck')


def add_phone(user_fp, phone_number):
    callchecker = get_callcheck()
    response = callchecker.add_phone(phone_number)
    return response

def check_phone(user_fp, phone_number):
    callchecker = get_callcheck()
    response = callchecker.check_phone(phone_number)
    return response == OK

