import web.logger as logger


from flask import redirect, session, url_for


from functools import wraps


def login_required(f):
    """Декоратор для проверки авторизации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f'session data {[item for item in session.items()]}')
        if not session.get('is_authenticated'):
            logger.debug('User is not authenticated')
            return redirect(url_for('admin.login'), 302)
        return f(*args, **kwargs)
    return decorated_function
