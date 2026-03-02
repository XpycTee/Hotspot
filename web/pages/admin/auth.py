from datetime import timedelta
from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for

from core.config import get_config
import web.logger as logger
from core.admin.auth.login import login_by_password
from web.pages.admin.utils import csrf_protection_enabled, ensure_csrf_token, login_required, validate_csrf_token


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def _set_error_and_log(message, username, client_ip):
    """Устанавливает сообщение об ошибке и записывает лог."""
    session['error'] = message
    logger.error(f"{message} for user {username} from {client_ip}")


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


def _build_lockout_key(username: str | None, client_ip: str | None) -> str:
    norm_username = (username or '').strip().lower() or '<anonymous>'
    norm_ip = (client_ip or '').strip() or '<unknown-ip>'
    return f'{norm_username}:{norm_ip}'


@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    ensure_csrf_token()
    error = session.pop('error', None)
    return render_template('admin/login.html', error=error)


@auth_bp.route('/check', methods=['POST'])
def check():
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr

    if csrf_protection_enabled():
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            abort(403)

    config = get_config()
    user_lang = request.form.get('language', config.language.name)

    lockout_key = _build_lockout_key(username, client_ip)

    response = login_by_password(lockout_key, username, password)
    status = response.get('status')

    if status == 'OK':
        session.clear()
        session['is_authenticated'] = True
        session['user_lang'] = user_lang if user_lang != 'auto' else None
        session['username'] = username
        ensure_csrf_token()
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=30)

        logger.info(f'User {username} logged in from {client_ip}')
        logger.debug(f'session data {_log_masked_session()}')
        return redirect(url_for('pages.admin.panel.index'), 302)

    if status == 'LOCKOUT':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.auth.login'), 302)

    if status == 'BAD_LOGIN':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.auth.login'), 302)

    abort(500, description="Unknown status")


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required(group='read')
def logout():
    session.clear()
    return redirect(url_for('pages.admin.auth.login'), 302)
