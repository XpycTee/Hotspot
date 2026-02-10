from random import randint

from core.logging import get_logger
from core.redis import cache
from core.config.authentificators import get_sender
from core.utils.language import get_translate


logger = get_logger('core.hotspot.auth.code')

def generate_code(user_fp):
    code = str(randint(0, 9999)).zfill(4)
    cache.set(f'sms:code:{user_fp}', code, 300)
    cache.set_raw(f'sms:attempts:{user_fp}', 0, 300)
    cache.set(f'sms:sended:{user_fp}', False, 60)
    return code

def get_code(user_fp):
    return cache.get(f"sms:code:{user_fp}")

def set_sended(user_fp):
    cache.set(f'sms:sended:{user_fp}', True, 60)

def increment_attempts(user_fp):
    return cache.incr(f"sms:attempts:{user_fp}")

def verify_code(user_fp, code: str):
    cached = cache.get(f"sms:code:{user_fp}")
    if cached:
        return cached == code
    
    return cached

def code_sended(user_fp):
    sended = cache.get(f"sms:sended:{user_fp}")
    return sended is not None and sended

def clear_code(user_fp):
    cache.delete(f'sms:code:{user_fp}')
    cache.delete(f'sms:attempts:{user_fp}')
    cache.delete(f'sms:sended:{user_fp}')


def send_code(user_fp, phone_number):
    if code_sended(user_fp):
        return {"status": "ALREDY_SENDED", 'error_message': get_translate("errors.auth.code_can_not_resend")}
    
    if user_code:=get_code(user_fp):
        logger.debug(f'User cached code for {phone_number}: {user_code}')
        sending_code = user_code
    else:
        sending_code = generate_code(user_fp)

    sender = get_sender()
    sms_error = sender.send_sms(phone_number, get_translate('sms_code', templates={"code": sending_code}))

    if sms_error:
        logger.error(f"Failed to send SMS to {phone_number}")
        return {"status": "SENDER_ERROR"}
    
    set_sended(user_fp)
    logger.debug(f"Send {phone_number}'s code: {sending_code}")
    return {"status": "OK"}
