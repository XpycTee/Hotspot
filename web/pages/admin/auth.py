from datetime import timedelta
from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for

import web.logger as logger
from core.admin.auth.login import login_by_password
from core.config.language import LANGUAGE_DEFAULT
from web.pages.admin import session


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


@auth_bp.route('/login', methods=['POST', 'GET'])
def login():
    error = session.pop('error', None)
    return render_template('admin/login.html', error=error)


@auth_bp.route('/check', methods=['POST'])
def check():
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr
    user_lang = request.form.get('language', LANGUAGE_DEFAULT)

    session_id = session.get('_id')

    response = login_by_password(session_id, username, password)
    status = response.get('status')

    if status == 'OK':
        session['is_authenticated'] = True
        session['user_lang'] = user_lang if user_lang != 'auto' else None
        session.permanent = True
        current_app.permanent_session_lifetime = timedelta(minutes=30)

        logger.info(f'User {username} logged in from {client_ip}')
        logger.debug(f'session data {_log_masked_session()}')
        return redirect(url_for('pages.admin.panel'), 302)

    if status == 'LOCKOUT':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.auth.login'), 302)

    if status == 'BAD_LOGIN':
        error_message = response.get('error_message')
        _set_error_and_log(error_message, username, client_ip)
        return redirect(url_for('pages.admin.auth.login'), 302)

    abort(500, description="Unknown status")


@auth_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()  # Очищаем сессию
    return redirect(url_for('pages.admin.auth.login'), 302)
