import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Blueprint, abort, render_template, redirect, url_for,
    session, request, current_app
)
from app.database import models
from extensions import cache

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def login_required(f):
    """Декоратор для проверки авторизации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('admin.login'), 302)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/', methods=['POST', 'GET'])
@login_required
def admin():
    return redirect(url_for('admin.panel'), 302)


@admin_bp.route('/login', methods=['POST', 'GET'])
def login():
    error = session.pop('error', None)
    return render_template('admin/login.html', error=error)


@admin_bp.route('/auth', methods=['POST'])
def auth():
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr

    # Проверка блокировки
    lockout_until = cache.get("lockout_until")
    lockout_time = current_app.config.get('LOCKOUT_TIME', 0)  # Установить значение по умолчанию
    if lockout_until and datetime.now().timestamp() < float(lockout_until):
        _set_error_and_log(
            f"Слишком много попыток. Повторите через {lockout_time} минут.",
            username, client_ip, "warning"
        )
        return redirect(url_for('admin.login'), 302)

    app_admin = current_app.config.get('ADMIN', {})
    if (
            app_admin and
            username == app_admin.get('username') and
            _check_password(password, app_admin.get('password'))
    ):
        _reset_login_attempts()
        session['is_authenticated'] = True
        current_app.logger.info(f'User {username} logged in from {client_ip}')
        return redirect(url_for('admin.panel'), 302)

    _handle_failed_login(username, client_ip)
    return redirect(url_for('admin.login'), 302)


@admin_bp.route('/panel', methods=['POST', 'GET'])
@login_required
def panel():
    error = session.pop('error', None)
    wifi_clients = []
    db_clients = models.WifiClient.query.all()
    for db_client in db_clients:
        if db_client:
            wifi_clients.append({
                'mac': db_client.mac,
                'expiration': db_client.expiration,
                'employee': db_client.employee,
                'phone': db_client.phone.phone_number
            })
    employees = current_app.config.get('EMPLOYEES', [])
    blacklist = current_app.config.get('BLACKLIST', [])
    return render_template(
        'admin/panel.html',
        wifi_clients=wifi_clients,
        employees=employees,
        blacklist=blacklist,
        error=error
    )


@admin_bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()  # Очищаем сессию
    return redirect(url_for('admin.login'), 302)


@admin_bp.route('/save/<tabel_name>', methods=['POST'])
@login_required
def save_data(tabel_name):
    data = request.json
    if tabel_name not in ['employee', 'blacklist']:
        abort(404)

    print(data)
    # Process and save data to the database
    # Return a JSON response
    return {'success': True}

@admin_bp.route('/delete/<tabel_name>', methods=['POST'])
@login_required
def delete_data(tabel_name):
    data = request.json
    if tabel_name not in ['employee', 'blacklist']:
        abort(404)

    print(data)
    # Process and save data to the database
    # Return a JSON response
    return {'success': True}


# Вспомогательные функции для повышения читаемости и повторного использования
def _check_password(password, stored_password_hash):
    """Проверяет хэш пароля."""
    if not stored_password_hash:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8'))


def _reset_login_attempts():
    """Сбрасывает попытки входа."""
    cache.delete("login_attempts")
    cache.delete("lockout_until")


def _handle_failed_login(username, client_ip):
    """Обрабатывает неудачную попытку входа."""
    login_attempts = cache.get("login_attempts") or 0
    login_attempts += 1

    max_login_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS')
    lockout_time = current_app.config.get('LOCKOUT_TIME')
    if login_attempts >= max_login_attempts:
        lockout_until = datetime.now() + timedelta(minutes=lockout_time)
        cache.set("lockout_until", lockout_until.timestamp(), timeout=lockout_time * 60)
        _set_error_and_log(f"Слишком много попыток. Повторите через {lockout_time} минут.",
                           username, client_ip, "critical")
    else:
        cache.set("login_attempts", login_attempts, timeout=lockout_time * 60)
        _set_error_and_log("Неверный логин или пароль", username, client_ip, "critical")


def _set_error_and_log(message, username, client_ip, log_level):
    """Устанавливает сообщение об ошибке и записывает лог."""
    session['error'] = message
    log_func = getattr(current_app.logger, log_level, current_app.logger.info)
    log_func(f'{message} for user {username} from {client_ip}')
