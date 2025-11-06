# Imports
import datetime
import logging
import re

from hashlib import md5
from random import randint
from typing import Any, ItemsView
import uuid

# Importing Blueprint for creating Flask blueprints
from flask import Blueprint, jsonify, make_response

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

import jmespath

import logger
from app.database import db
from app.database.models import Blacklist, ClientsNumber, EmployeePhone, WifiClient
from extensions import fetch_employees, get_translate, cache, normalize_phone

auth_bp = Blueprint('auth', __name__)


def _octal_string_to_bytes(oct_string):
    if not oct_string:
        return b''
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
    """Проверка, является ли номер телефона сотрудником."""
    employees = fetch_employees()  # Используем кешированные данные
    sova_phone_number = re.sub(r'^(\+?7|8)', '', phone_number) if phone_number else ''
    expression = f"employee[].phone[].number | contains([], '{sova_phone_number}')"
    in_base = bool(jmespath.search(expression, employees))
    if not in_base:
        # Проверка наличия номера телефона в базе данных сотрудников
        employee_phone = EmployeePhone.query.filter_by(phone_number=phone_number).first()
        return employee_phone is not None
    return in_base


def _get_today() -> datetime.datetime:
    return datetime.datetime.combine(
        datetime.date.today(),
        datetime.time(6, 0)
    )

def _mask_phone(phone: str) -> str:
    return '*'*(len(phone)-4) + phone[-4:]

def _mask_mac(mac: str) -> str:
    parts = re.split(r'[:-]', mac)
    return 'XX:XX:XX:' + ':'.join(parts[3:])

def _mask_sensetive_session(session: ItemsView[str, Any]):
    sensetive = ["chap-id", "chap-challenge", "password"]
    result = {}
    for k, v in session:
        if k == "phone":
            result[k] = _mask_phone(v)
        elif k == "mac":
            result[k] = _mask_mac(v)
        elif k in sensetive:
            result[k] = '******'
        else:
            result[k] = v

    return result

@auth_bp.route('/', methods=['POST', 'GET'])
def index():
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    if not has_form and not has_session:
        if 'link-orig' not in session.keys():
            abort(400)
        else:
            redirect(session.get('link-orig'), 302)

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

    now_time = datetime.datetime.now()
    db_phone = _get_or_create_client(phone_number)
    # Обновляем поле last_seen, если запись уже существует
    try:
        db_phone.last_seen = now_time
        db.session.commit()
        logger.debug(f"Update time {now_time} for number {_mask_phone(phone_number)}")
    except IntegrityError:
        db.session.rollback()
        logger.error("Failed to update last_seen for phone number: %s", _mask_phone(phone_number))
    
    return render_template(
        'auth/sendin.html', 
        link_login_only=link_login_only, 
        username=username,
        password=password,
        link_orig=link_orig
    )


@auth_bp.route('/test_login', methods=['GET'])
def test_login():
    if not current_app.debug:
        abort(404)
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_requirements = all(key in set(request.values.keys()) for key in required_keys)
    if not has_requirements:
        abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]
        logger.debug(f'Session data in test: {_mask_sensetive_session(session.items())}')
    return login()


@auth_bp.route('/login', methods=['POST'])
def login():
    error = session.pop('error', None)

    auth_id_cookie = request.cookies.get('auth_id', "Empty")
    logger.debug(f"Cookie auth_id: {auth_id_cookie}")
    
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    logger.debug(f'Session data before form: {_mask_sensetive_session(session.items())}')

    if not has_form and not has_session:
        abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]

    logger.debug(f'Session data after form: {_mask_sensetive_session(session.items())}')
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
    logger.debug(f'Session data before code: {_mask_sensetive_session(session.items())}')
    phone_number = request.form.get('phone')

    if phone_number:
        phone_number = normalize_phone(phone_number)

        if Blacklist.query.filter_by(phone_number=phone_number).first():
            abort(403)

        session['phone'] = phone_number

        mac = session.get('mac')
        logger.debug(f'User mac: {_mask_mac(mac)}')
        if not mac:
            abort(400)

        db_client = WifiClient.query.filter_by(mac=mac).first()

        if db_client and db_client.phone and (db_client.phone.phone_number == phone_number or db_client.phone.phone_number == phone_number[1:]):
            is_employee = _check_employee(phone_number)

            users_config = current_app.config['HOTSPOT_USERS']

            hotspot_user = users_config['employee'] if is_employee else users_config['guest']

            today_start = _get_today()
            delay = hotspot_user.get('delay')
            expire_time = today_start + delay
            if expire_time < datetime.datetime.now():
                expire_time += datetime.timedelta(days=1)

            db_client.expiration = expire_time
            db_client.employee = is_employee
            db.session.commit()
            redirect_url = url_for('auth.sendin')
            response = redirect(redirect_url, 302)
            client_uuid = uuid.uuid5(name=f"{mac}/{phone_number}", namespace=uuid.NAMESPACE_DNS)
            response.set_cookie("auth_id", client_uuid, delay)
            return response

    # Ensure phone_number is retrieved from session if not provided in the request
    if not phone_number:
        phone_number = session.get('phone')
        logger.debug(f'User phone: {_mask_phone(phone_number)}')
        if not phone_number:
            abort(400)

    if not cache.get(f'code_{phone_number}'):
        gen_code = str(randint(0, 9999)).zfill(4)
        cache.set(f'code_{phone_number}', gen_code, timeout=5 * 60)
        cache.set(f'dont_resend_{phone_number}', "true", timeout=60)

        sender = current_app.config.get('SENDER')
        sms_error = sender.send_sms(phone_number, get_translate('sms_code').format(code=gen_code))

        if sms_error:
            logger.error(f"Failed to send SMS to {_mask_phone(phone_number)}")
            abort(500)

        logger.debug(f"{_mask_phone(phone_number)}'s code: {gen_code}")

    return render_template('auth/code.html', error=error)


@auth_bp.route('/resend', methods=['POST'])
def resend():
    phone_number = session.get('phone')
    logger.debug(f'Session data before code: {_mask_sensetive_session(session.items())}')
    if not phone_number:
        abort(400)
    if cache.get(f'dont_resend_{phone_number}'):
        abort(400, description=get_translate('errors.auth.code_alredy_sended'))

    user_code = cache.get(f'code_{phone_number}')
    logger.debug(f'User cached code for {_mask_phone(phone_number)}: {user_code}')

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

    logger.debug(f"Resend {_mask_phone(phone_number)}'s code: {resend_code}")

    return jsonify({'success': True})


def _get_or_create_client(phone_number):
    """Получить или создать запись клиента по номеру телефона."""
    now_time = datetime.datetime.now()
    db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
    if not db_phone:
        try:
            db_phone = ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db.session.add(db_phone)
            db.session.commit()
            logger.debug(f"Create new number {_mask_phone(phone_number)} by time {now_time}")
        except IntegrityError:
            db.session.rollback()
            db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
    return db_phone


def _create_or_udpate_wifi_client(mac, expiration, is_employee, db_phone):
    """Создать запись WiFi клиента по MAC-адресу, если нету."""
    db_client = db.session.execute(
        select(WifiClient).where(WifiClient.mac == mac).with_for_update()
    ).scalar_one_or_none()

    if not db_client:
        try:
            db_client = WifiClient(mac=mac, expiration=expiration, employee=is_employee, phone=db_phone)
            db.session.add(db_client)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    else:
        try:
            db_client.expiration = expiration
            db_client.employee = is_employee
            db_client.phone = db_phone
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


@auth_bp.route('/auth', methods=['POST'])
def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    if not mac or not phone_number:
        abort(400)
    
    form_code = request.form.get('code')
    user_code = cache.get(f'code_{phone_number}')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        return redirect(url_for('auth.code'), 302)
    if user_code is None:
        session['error'] = get_translate('errors.auth.expired_code')
        return redirect(url_for('auth.code'), 302)

    if int(form_code) == int(user_code):
        today_start = _get_today()

        # Получение или создание записи клиента
        db_phone = _get_or_create_client(phone_number)

        # Проверка, является ли пользователь сотрудником
        is_employee = _check_employee(phone_number)

        # Обновление времени истечения
        users_config = current_app.config['HOTSPOT_USERS']
        hotspot_user = users_config['employee'] if is_employee else users_config['guest']
        delay = hotspot_user.get('delay')
        expire_time = today_start + delay
        if expire_time < datetime.datetime.now():
            expire_time += datetime.timedelta(days=1)

        _create_or_udpate_wifi_client(mac, expire_time, is_employee, db_phone)

        response = redirect(url_for('auth.sendin'), 302)
        client_uuid = uuid.uuid5(name=f"{mac}/{phone_number}", namespace=uuid.NAMESPACE_DNS)
        response.set_cookie("auth_id", client_uuid, delay)

        # Очистка кэша и редирект
        cache.delete(f'code_{phone_number}')
        return response
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
