from core.admin.security.access import has_access
import web.logger as logger


from flask import abort, current_app, redirect, request, session, url_for

import secrets
from hmac import compare_digest

from functools import wraps


UNSAFE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
CSRF_SESSION_KEY = 'csrf_token'
CSRF_HEADER = 'X-CSRF-Token'


def _log_masked_session():
    sensetive = []
    result = {}
    items = session.items()
    for k, v in items:
        if k.startswith("_"):
            continue
        elif k in sensetive:
            result[k] = '******'
        else:
            result[k] = v
    return result


def ensure_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(token: str | None) -> bool:
    session_token = session.get(CSRF_SESSION_KEY)
    if not session_token or not token:
        return False
    return compare_digest(str(session_token), str(token))


def csrf_token_from_request() -> str | None:
    return (
        request.headers.get(CSRF_HEADER)
        or request.form.get('csrf_token')
        or request.args.get('csrf_token')
    )


def csrf_protection_enabled() -> bool:
    enabled = current_app.config.get('ADMIN_CSRF_ENABLED')
    if enabled is not None:
        return bool(enabled)
    return not (current_app.testing or current_app.debug)


def login_required(_func=None, *, group='read'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f'session data {_log_masked_session()}')

            if not session.get('is_authenticated'):
                logger.debug('User is not authenticated')
                return redirect(url_for('pages.admin.auth.login'), 302)

            username = session.get('username')
            if not username:
                session.clear()
                return redirect(url_for('pages.admin.auth.login'), 302)

            if request.method in UNSAFE_METHODS and csrf_protection_enabled():
                token = csrf_token_from_request()
                if not validate_csrf_token(token):
                    return abort(403)
            else:
                ensure_csrf_token()

            if not has_access(username, group):
                return abort(403)

            return f(*args, **kwargs)
        return decorated_function

    if _func is not None:
        return decorator(_func)

    return decorator
