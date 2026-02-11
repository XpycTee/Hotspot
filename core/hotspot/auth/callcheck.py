from random import randint

from core.config.response_code import OK
from core.hotspot.auth.confirm import auth_confirm
from core.logging import get_logger
from core.redis import cache
from core.config.authentificators import get_callcheck
from core.utils.language import get_translate


logger = get_logger('core.hotspot.auth.callcheck')


def add_phone(user_fp, phone_number):
    callchecker = get_callcheck()
    response = callchecker.add_phone(phone_number)
    return response

def check_phone(user_fp, phone_number):
    callchecker = get_callcheck()
    response = callchecker.check_phone(phone_number)
    return response == OK

