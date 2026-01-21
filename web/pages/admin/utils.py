from core.admin.security.access import has_access
import web.logger as logger


from flask import abort, redirect, request, session, url_for


from functools import wraps


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


def login_required(_func=None, *, group='read'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            logger.debug(f'session data {_log_masked_session()}')

            if not session.get('is_authenticated'):
                logger.debug('User is not authenticated')
                return redirect(url_for('pages.admin.auth.login'), 302)

            if not has_access(session['username'], group):
                return abort(403)

            return f(*args, **kwargs)
        return decorated_function

    if _func is not None:
        return decorator(_func)

    return decorator
