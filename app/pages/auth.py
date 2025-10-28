# Imports
import datetime
import re

from hashlib import md5
from random import randint

# Importing Blueprint for creating Flask blueprints
from flask import Blueprint, jsonify

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

# Importing functions for rendering templates, redirecting, generating URLs, and aborting requests
from flask import (
    render_template,
    redirect,
    url_for,
    abort
)

# Importing session for session management, request for handling HTTP requests, and current_app for accessing the Flask application context
from flask import (
    session,
    request,
    current_app
)

from app.database import db
from app.database.models import Blacklist, ClientsNumber, EmployeePhone, WifiClient
from extensions import get_translate, cache

auth_bp = Blueprint('auth', __name__)


def _octal_string_to_bytes(oct_string):
    # Split the octal string by backslash and process each part
    byte_nums = []
    for octal_num in oct_string.split("\\")[1:]:
        decimal_value = 0
        # Convert each octal digit to decimal and sum up the values
        for i in range(len(octal_num)):
            decimal_value += int(octal_num[-(i + 1)]) * 8 ** i
        byte_nums.append(decimal_value)
    # Convert the list of decimal values to bytes
    return bytes(byte_nums)


def _check_employee(phone_number):
    # Проверка наличия номера телефона в базе данных сотрудников
    employee_phone = EmployeePhone.query.filter_by(phone_number=phone_number).first()
    return employee_phone is not None


@auth_bp.route('/', methods=['POST', 'GET'])
def index():
    required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']
    if not any(key in set(request.form.keys()) for key in required_keys) or \
        not any(key in set(session.keys()) for key in required_keys):
            if 'link-orig' not in session.keys():
                abort(400)
            else:
                redirect(session.get('link-orig'), 302)
    else:
        return redirect(url_for('auth.login'), 302)


@auth_bp.route('/sendin', methods=['POST', 'GET'])
def sendin():
    phone_number = session.get('phone')
    if not phone_number:
        abort(400)

    is_employee = _check_employee(phone_number)

    username = 'employee' if is_employee else 'guest'
    password = current_app.config['HOTSPOT_USERS'][username].get('password')
    if not password:
        abort(500)

    link_login_only = session.get('link-login-only')
    link_orig = session.get('link-orig')

    chap_id = session.get('chap-id')
    chap_challenge = session.get('chap-challenge')
    
    # use HTTP CHAP method in hotspot
    if chap_id and chap_challenge:
        chap_id = _octal_string_to_bytes(chap_id)
        chap_challenge = _octal_string_to_bytes(chap_challenge)
        link_login_only = link_login_only.replace('https', 'http')
        password = md5(chap_id + password.encode() + chap_challenge).hexdigest()

    cache.delete(f'code_{phone_number}')
    session.clear()
    session['link-orig'] = link_orig

    db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
    now_time = datetime.datetime.now()
    # Обновляем поле last_seen, если запись уже существует
    try:
        db_phone.last_seen = now_time
        db.session.commit()
        current_app.logger.debug(f"Update time {now_time} for number {phone_number}")
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error("Failed to update last_seen for phone number: %s", phone_number)
    return f"""
    <html>
        <body onload="document.forms[0].submit()">
            <form action="{link_login_only}" method="post">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="password" value="{password}">
                <input type="hidden" name="dst" value="{link_orig}">
                <input type="hidden" name="popup" value="true">
            </form>
        </body>
    </html>
    """


@auth_bp.route('/test_login', methods=['GET'])
def test_login():
    if not current_app.debug:
        abort(404)
    required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']
    result = [key in set(request.values.keys()) for key in required_keys]
    if not any(result):
        abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]
        current_app.logger.debug(f'Session data in test: {[item for item in session.items()]}')
    return login()


@auth_bp.route('/login', methods=['POST'])
def login():
    error = session.pop('error', None)

    required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']

    current_app.logger.debug(f'Session data before form: {[item for item in session.items()]}')

    if not any(key in set(request.form.keys()) for key in required_keys):
        if not any(key in set(session.keys()) for key in required_keys):
            abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]

    current_app.logger.debug(f'Session data after form: {[item for item in session.items()]}')
    mac = session.get('mac')

    db_client = WifiClient.query.filter_by(mac=mac).first()
    if db_client and datetime.datetime.now() < db_client.expiration:
        phone = db_client.phone
        if not phone:
            abort(500)

        if Blacklist.query.filter_by(phone_number=phone.phone_number).first():
            abort(403)
        
        if _check_employee(phone.phone_number) == db_client.employee:
            session['phone'] = phone.phone_number

            redirect_url = url_for('auth.sendin')
            return redirect(redirect_url, 302)

    return render_template('auth/login.html', error=error)


@auth_bp.route('/code', methods=['POST', 'GET'])
def code():
    error = session.pop('error', None)
    current_app.logger.debug(f'Session data before code: {[item for item in session.items()]}')
    phone_number = request.form.get('phone')

    if phone_number:
        phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
        phone_number = re.sub(r'\D', '', phone_number)

        if Blacklist.query.filter_by(phone_number=phone_number).first():
            abort(403)

        session['phone'] = phone_number

        mac = session.get('mac')
        current_app.logger.debug(f'User mac: {mac}')
        if not mac:
            abort(400)

        db_client = WifiClient.query.filter_by(mac=mac).first()

        if db_client and db_client.phone and db_client.phone.phone_number == phone_number:
            is_employee = _check_employee(phone_number)

            users_config = current_app.config['HOTSPOT_USERS']

            hotspot_user = users_config['employee'] if is_employee else users_config['guest']

            expire_time = datetime.datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
            if expire_time < datetime.datetime.now():
                expire_time += datetime.timedelta(days=1)

            db_client.expiration = expire_time + hotspot_user.get('delay')
            db_client.employee = is_employee
            db.session.commit()
            redirect_url = url_for('auth.sendin')
            return redirect(redirect_url, 302)

    # Ensure phone_number is retrieved from session if not provided in the request
    if not phone_number:
        phone_number = session.get('phone')
        current_app.logger.debug(f'User phone: {phone_number}')
        if not phone_number:
            abort(400)

    if not cache.get(f'code_{phone_number}'):
        gen_code = str(randint(0, 9999)).zfill(4)
        cache.set(f'code_{phone_number}', gen_code, timeout=5 * 60)
        cache.set(f'dont_resend_{phone_number}', "true", timeout=60)

        sender = current_app.config.get('SENDER')
        sms_error = sender.send_sms(phone_number, get_translate('sms_code').format(code=gen_code))

        if sms_error:
            current_app.logger.error(f"Failed to send SMS to {phone_number}")
            abort(500)

        current_app.logger.debug(f"{phone_number}'s code: {gen_code}")

    return render_template('auth/code.html', error=error)


@auth_bp.route('/resend', methods=['POST'])
def resend():
    phone_number = session.get('phone')
    current_app.logger.debug(f'Session data before code: {[item for item in session.items()]}')
    if not phone_number:
        abort(400)
    if cache.get(f'dont_resend_{phone_number}'):
        abort(400, description=get_translate('errors.auth.code_alredy_sended'))

    user_code = cache.get(f'code_{phone_number}')
    current_app.logger.debug(f'User cached code for {phone_number}: {user_code}')

    if not user_code:
        resend_code = str(randint(0, 9999)).zfill(4)
        cache.set(f'code_{phone_number}', resend_code, timeout=5 * 60)
    else:
        resend_code = user_code
    cache.set(f'dont_resend_{phone_number}', "true", timeout=60)

    sender = current_app.config.get('SENDER')
    sms_error = sender.send_sms(phone_number, get_translate('sms_code').format(code=resend_code))
    if sms_error:
        abort(500)

    current_app.logger.debug(f"Resend {phone_number}'s code: {resend_code}")

    return jsonify({'success': True})


def _get_or_create_client(phone_number, now_time):
    """Получить или создать запись клиента по номеру телефона."""
    db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
    if not db_phone:
        try:
            db_phone = ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db.session.add(db_phone)
            db.session.commit()
            current_app.logger.debug(f"Create new number {phone_number} by time {now_time}")
        except IntegrityError:
            db.session.rollback()
            db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
    return db_phone


def _create_wifi_client_if_not_exitst(mac, now_time, is_employee, db_phone):
    """Создать запись WiFi клиента по MAC-адресу, если нету."""
    db_client = db.session.execute(
        select(WifiClient).where(WifiClient.mac == mac).with_for_update()
    ).scalar_one_or_none()

    if not db_client:
        try:
            db_client = WifiClient(mac=mac, expiration=now_time, employee=is_employee, phone=db_phone)
            db.session.add(db_client)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def _update_expiration(mac, delay):
    """Обновить время истечения для WiFi клиента."""
    expire_time = datetime.datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    try:
        db.session.execute(
            update(WifiClient)
            .where(WifiClient.mac == mac)
            .values(expiration=expire_time + delay)
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.error("Failed to update expiration for MAC: %s", mac)


@auth_bp.route('/auth', methods=['POST'])
def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = request.form.get('code')
    user_code = cache.get(f'code_{phone_number}')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        return redirect(url_for('auth.code'), 302)
    if user_code is None:
        session['error'] = get_translate('errors.auth.expired_code')
        return redirect(url_for('auth.code'), 302)

    if int(form_code) == int(user_code):
        now_time = datetime.datetime.now()

        # Получение или создание записи клиента
        db_phone = _get_or_create_client(phone_number, now_time)

        # Проверка, является ли пользователь сотрудником
        is_employee = _check_employee(phone_number)

        # Получение или создание записи WiFi клиента
        _create_wifi_client_if_not_exitst(mac, now_time, is_employee, db_phone)

        # Обновление времени истечения
        users_config = current_app.config['HOTSPOT_USERS']
        hotspot_user = users_config['employee'] if is_employee else users_config['guest']
        _update_expiration(mac, hotspot_user.get('delay'))

        # Очистка кэша и редирект
        cache.delete(f'code_{phone_number}')
        return redirect(url_for('auth.sendin'), 302)
    else:
        session.setdefault('tries', 0)
        session['tries'] += 1

        if session['tries'] >= 3:
            session['error'] = get_translate('errors.auth.bad_code_all')
            session.pop('tries', None)
            session.pop('phone', None)
            cache.delete(f'code_{phone_number}')
            return redirect(url_for('auth.login'), 302)
        else:
            session['error'] = get_translate('errors.auth.bad_code_try')
            return redirect(url_for('auth.code'), 307)
