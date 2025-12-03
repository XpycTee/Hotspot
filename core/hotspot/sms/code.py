from random import randint

from core.logging.logger import logger
from core.cache import get_cache
from core.config.sms import get_sender
from core.utils.language import get_translate


def generate_code(session_id):
    cache = get_cache()
    code = str(randint(0, 9999)).zfill(4)
    cache.set(f'sms:code:{session_id}', code, timeout=300)
    cache.set(f'sms:attempts:{session_id}', 0, timeout=300)
    cache.set(f'sms:sended:{session_id}', False, timeout=60)
    return code

def get_code(session_id):
    cache = get_cache()
    return cache.get(f"sms:code:{session_id}")

def set_sended(session_id):
    cache = get_cache()
    cache.set(f'sms:sended:{session_id}', True, timeout=60)

def increment_attempts(session_id):
    cache = get_cache()
    cache.inc(f"sms:attempts:{session_id}")
    return cache.get(f"sms:attempts:{session_id}")

def verify_code(session_id, code):
    cache = get_cache()
    cached = cache.get(f"sms:code:{session_id}")
    return cached and cached == code

def code_sended(session_id):
    cache = get_cache()
    return cache.get(f"sms:sended:{session_id}")

def clear_code(session_id):
    cache = get_cache()
    cache.delete(f'sms:code:{session_id}')
    cache.delete(f'sms:attempts:{session_id}')
    cache.delete(f'sms:sended:{session_id}')


def send_code(session_id, phone_number):
    resp = {"status": "OK"}

    if code_sended(session_id):
        resp = {"status": "ALREDY_SENDED", 'error_message': get_translate("errors.auth.code_can_not_resend")}
        return resp
    
    if user_code:=get_code(session_id):
        logger.debug(f'User cached code for {phone_number}: {user_code}')
        sending_code = user_code
    else:
        sending_code = generate_code(session_id)

    sender = get_sender()
    sms_error = sender.send_sms(phone_number, get_translate('sms_code', templates={"code": sending_code}))

    if sms_error:
        logger.error(f"Failed to send SMS to {phone_number}")
        resp = {"status": "SENDER_ERROR"}
        return resp
    
    set_sended(session_id)
    logger.debug(f"Send {phone_number}'s code: {sending_code}")
    return resp

