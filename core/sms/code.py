import logging
from random import randint

from core.sms.sender import DebugSender
from app.utils.language import get_translate


def generate_code(session_id):
    code = str(randint(0, 9999)).zfill(4)
    cache.set(f'{session_id}:sms:code', code, timeout=300)
    cache.set(f'{session_id}:sms:attempts', 0, timeout=300)
    cache.set(f'{session_id}:sms:sended', False, timeout=60)
    return code

def get_code(session_id):
    return cache.get(f"{session_id}:sms:code")

def set_sended(session_id):
    cache.set(f'{session_id}:sms:sended', True, timeout=60)

def increment_attempts(session_id):
    attempts = cache.get(f"{session_id}:sms:attempts") or 0
    attempts += 1
    cache.set(f'{session_id}:sms:attempts', attempts, timeout=300)
    return attempts

def verify_code(session_id, code):
    cached = cache.get(f"{session_id}:sms:code")
    return cached and cached == code

def code_sended(session_id):
    return cache.get(f"{session_id}:sms:sended")

def clear_code(session_id):
    cache.delete(f'{session_id}:sms:code')
    cache.delete(f'{session_id}:sms:attempts')
    cache.delete(f'{session_id}:sms:sended')


def send_code(session_id, phone_number):
    resp = {"status": "OK"}

    if code_sended(session_id):
        resp = {"status": "ALREDY_SENDED"}
        return resp
    
    if user_code:=get_code(session_id):
        logging.debug(f'User cached code for {phone_number}: {user_code}')
        sending_code = user_code
    else:
        sending_code = generate_code(session_id)

    #sender = current_app.config.get('SENDER')
    # TODO Refactor getting sender
    sender = DebugSender()
    sms_error = sender.send_sms(phone_number, get_translate('sms_code', templates={"code": sending_code}))

    if sms_error:
        logging.error(f"Failed to send SMS to {phone_number}")
        resp = {"status": "BAD_SMS"}
        return resp
    
    set_sended(session_id)
    logging.debug(f"Send {phone_number}'s code: {sending_code}")
    return resp

