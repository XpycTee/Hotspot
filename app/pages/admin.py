import re
import bcrypt
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint, abort, render_template, redirect, url_for,
    session, request, current_app, jsonify
)
from app.database import db
from app.database.models import WifiClient, Employee, EmployeePhone, Blacklist
from extensions import cache, get_translate

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
    user_lang = request.form.get('language', current_app.config.get('LANGUAGE_DEFAULT'))  # Получаем язык из формы, по умолчанию 'en'

    # Проверка блокировки
    lockout_until = cache.get("lockout_until")
    lockout_time = current_app.config.get('LOCKOUT_TIME', 0)  # Установить значение по умолчанию
    if lockout_until and datetime.now().timestamp() < float(lockout_until):
        _set_error_and_log(
            get_translate('errors.admin.end_tries').format(lockout_time=lockout_time),
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
        # Сохраняем язык пользователя в кеш
        session["user_lang"] = user_lang if user_lang != 'auto' else None
        session.permanent = True  # Устанавливаем сессию как постоянную
        current_app.permanent_session_lifetime = timedelta(minutes=30)  # Время жизни сессии
        
        current_app.logger.info(get_translate('errors.admin.user_logged_in').format(username=username, client_ip=client_ip))

        return redirect(url_for('admin.panel'), 302)

    _handle_failed_login(username, client_ip)
    return redirect(url_for('admin.login'), 302)


@admin_bp.route('/panel', methods=['POST', 'GET'])
@login_required
def panel():
    error = session.pop('error', None)
    wifi_clients = WifiClient.query.all()
    employees = Employee.query.all()
    blacklist = Blacklist.query.all()

    wifi_clients_data = [
        {
            'mac': client.mac,
            'expiration': client.expiration,
            'employee': client.employee,
            'phone': client.phone.phone_number
        }
        for client in wifi_clients
    ]

    employees_data = [
        {
            'id': emp.id,
            'lastname': emp.lastname,
            'name': emp.name,
            'phones': [phone.phone_number for phone in emp.phones]
        }
        for emp in employees
    ]
    blacklist_data = [entry.phone_number for entry in blacklist]

    return render_template(
        'admin/panel.html',
        wifi_clients=wifi_clients_data,
        employees=employees_data,
        blacklist=blacklist_data,
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
    new_id = None

    if not data:
        return jsonify({'error': get_translate('errors.admin.tables.missing_request_data')}), 400

    if tabel_name == 'employee':
        emp_id = data.get('id')
        if emp_id is not None:
            employee = Employee.query.filter_by(id=emp_id).first()
            if not employee:
                return jsonify({'error': get_translate('errors.admin.tables.employee_not_found')}), 404

            # Обновление существующего сотрудника
            employee.lastname = data['lastname']
            employee.name = data['name']

            # Обновление телефонов сотрудника
            existing_phones = {phone.phone_number for phone in employee.phones}
            new_phones = set()

            for phone_number in data['phone']:
                phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
                phone_number = re.sub(r'\D', '', phone_number)
                new_phones.add(phone_number)

            # Удаление старых телефонов
            for phone in employee.phones:
                if phone.phone_number not in new_phones:
                    db.session.delete(phone)

            # Добавление новых телефонов
            for phone_number in new_phones - existing_phones:
                new_phone = EmployeePhone(phone_number=phone_number, employee=employee)
                db.session.add(new_phone)
        else:
            # Создание нового сотрудника
            new_employee = Employee(lastname=data['lastname'], name=data['name'])
            db.session.add(new_employee)
            db.session.flush()  # Чтобы получить ID нового сотрудника

            # Добавление телефонов
            for phone_number in data['phone']:
                phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
                phone_number = re.sub(r'\D', '', phone_number)
                if EmployeePhone.query.filter_by(phone_number=phone_number).first():
                    return jsonify({'error': get_translate('errors.admin.tables.phone_number_exists')}), 400
                new_phone = EmployeePhone(phone_number=phone_number, employee=new_employee)
                db.session.add(new_phone)
            new_id = new_employee.id
        db.session.commit()
    elif tabel_name == 'blacklist':
        if Blacklist.query.filter_by(phone_number=data['phone']).first():
            return jsonify({'error': get_translate('errors.admin.tables.phone_number_exists')}), 400
        
        phone_number = re.sub(r'^(\+?7|8)', '7', data['phone'])
        phone_number = re.sub(r'\D', '', phone_number)

        new_blacklist_entry = Blacklist(phone_number=phone_number)
        db.session.add(new_blacklist_entry)
        db.session.commit()
    else:
        abort(404)

    response = {'success': True}
    if new_id:
        response.update({'new_id': new_id})
    return jsonify(response)

@admin_bp.route('/delete/<tabel_name>', methods=['POST'])
@login_required
def delete_data(tabel_name):
    data = request.json

    if not data:
        return jsonify({'error': get_translate('errors.admin.tables.missing_request_data')}), 400

    if tabel_name == 'employee':
        emp_id = data.get('id')
        if emp_id is None:
            return jsonify({'error': get_translate('errors.admin.tables.employee_not_found')}), 400
        
        employee = Employee.query.filter_by(id=emp_id).first()

        if not employee:
            return jsonify({'error': get_translate('errors.admin.tables.employee_not_found')}), 404

        # Удаление всех связанных телефонов
        for phone in employee.phones:
            db.session.delete(phone)
        db.session.delete(employee)
        db.session.commit()
    elif tabel_name == 'blacklist':
        blacklist_entry = Blacklist.query.filter_by(phone_number=data['phone']).first()
        if blacklist_entry:
            db.session.delete(blacklist_entry)
            db.session.commit()
    else:
        abort(404)

    return jsonify({'success': True})


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
        _set_error_and_log(get_translate('errors.admin.end_tries').format(lockout_time=lockout_time), username, client_ip, "critical")
    else:
        cache.set("login_attempts", login_attempts, timeout=lockout_time * 60)
        _set_error_and_log(get_translate('errors.admin.wrong_credentials'), username, client_ip, "critical")


def _set_error_and_log(message, username, client_ip, log_level):
    """Устанавливает сообщение об ошибке и записывает лог."""
    session['error'] = message
    log_func = getattr(current_app.logger, log_level, current_app.logger.info)
    log_func(get_translate('errors.admin.log').format(message=message, username=username, client_ip=client_ip))
