from core.admin.auth.attempts import increment_attempts, reset_attempts
from core.admin.auth.lockout import check_lockout, update_lockout
from core.admin.auth.security import check_password
import web.logger as logger
from core.config.admin import ADMIN
from core.utils.language import get_translate


def handle_failed_login(session_id):
    login_attempts = increment_attempts(session_id)
    max_login_attempts = ADMIN.get('max_login_attempts')
    if login_attempts >= max_login_attempts:
        update_lockout(session_id)
        lockout_time = ADMIN.get('lockout_time')
        error_message = get_translate('errors.admin.end_tries', templates={'lockout_time': lockout_time})
    else:
        error_message = get_translate('errors.admin.wrong_credentials')

    return error_message


def login_by_password(session_id, username, password):
    logger.info(f'Start login by {username}')

    if check_lockout(session_id):
        lockout_time = ADMIN.get('lockout_time')
        error_message = get_translate('errors.admin.end_tries', templates={'lockout_time': lockout_time})
        return {'status': 'LOCKOUT', 'error_message': error_message}

    if check_password(username, password):
        reset_attempts(session_id)
        return {'status': 'OK'}

    error_message = handle_failed_login(session_id)
    return {'status': 'BAD_LOGIN', 'error_message': error_message}
