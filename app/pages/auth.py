# Imports
import datetime
import re

from hashlib import md5
from random import randint

# Importing Blueprint for creating Flask blueprints
from flask import Blueprint, jsonify

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
from app.database.models import Blacklist, ClientsNumber, Employee, EmployeePhone, WifiClient
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

    return render_template(
        'auth/sendin.html',
        username=username,
        password=password,
        link_login_only=link_login_only,
        link_orig=link_orig
    )

@auth_bp.route('/test_login', methods=['GET'])
def test_login():
    if not current_app.debug:
        abort(404)
    required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']
    if not any(key in set(request.values.keys()) for key in required_keys):
        abort(400)
    else:
        session['chap-id'] = request.values.get('chap-id')
        session['chap-challenge'] = request.values.get('chap-challenge')
        session['link-login-only'] = request.values.get('link-login-only')
        session['link-orig'] = request.values.get('link-orig')
        session['mac'] = request.values.get('mac')
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
        session['chap-id'] = request.form.get('chap-id')
        session['chap-challenge'] = request.form.get('chap-challenge')
        session['link-login-only'] = request.form.get('link-login-only')
        session['link-orig'] = request.form.get('link-orig')
        session['mac'] = request.form.get('mac')

    current_app.logger.debug(f'Session data after form: {[item for item in session.items()]}')
    mac = session.get('mac')

    db_client = WifiClient.query.filter_by(mac=mac).first()
    if db_client and datetime.datetime.now() < db_client.expiration:
        phone = db_client.phone
        if not phone:
            abort(500)
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
        cache.set(f'code_{phone_number}', gen_code, timeout=300)

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

    user_code = cache.get(f'code_{phone_number}')
    current_app.logger.debug(f'User cached code for {phone_number}: {user_code}')

    if not user_code:
        resend_code = str(randint(0, 9999)).zfill(4)
        cache.set(f'code_{phone_number}', resend_code, timeout=300)
    else:
        resend_code = user_code

    sender = current_app.config.get('SENDER')
    sms_error = sender.send_sms(phone_number, get_translate('sms_code').format(code=resend_code))
    if sms_error:
        abort(500)

    current_app.logger.debug(f"Resend {phone_number}'s code: {resend_code}")

    return jsonify({'success': True})


@auth_bp.route('/auth', methods=['POST'])
def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = request.form.get('code')
    user_code = cache.get(f'code_{phone_number}')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        redirect_url = url_for('auth.code')
        return redirect(redirect_url, 302)
    if user_code is None:
        session['error'] = get_translate('errors.auth.expired_code')
        redirect_url = url_for('auth.code')
        return redirect(redirect_url, 302)

    form_code = int(form_code)
    user_code = int(user_code)

    if form_code == user_code:
        now_time = datetime.datetime.now()

        db_phone = ClientsNumber.query.filter_by(phone_number=phone_number).first()
        if not db_phone:
            db_phone = ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db.session.add(db_phone)
            db.session.commit()
        
        is_employee = _check_employee(phone_number)

        db_client = WifiClient.query.filter_by(mac=mac).first()
        if not db_client:
            db_client = WifiClient(mac=mac, expiration=now_time, employee=is_employee, phone=db_phone)
            db.session.add(db_client)
        else:
            db_client.phone = db_phone
            db_client.employee = is_employee

        users_config = current_app.config['HOTSPOT_USERS']
        hotspot_user = users_config['employee'] if is_employee else users_config['guest']

        delay = hotspot_user.get('delay')
        expire_time = datetime.datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        db_client.expiration = expire_time + delay

        db.session.commit()

        redirect_url = url_for('auth.sendin')
        return redirect(redirect_url, 302)
    else:
        session.setdefault('tries', 0)
        session['tries'] += 1

        if session['tries'] >= 3:
            session['error'] = get_translate('errors.auth.bad_code_all')
            session.pop('code', None)
            session.pop('tries', None)
            session.pop('phone', None)

            redirect_url = url_for('auth.login')
            return redirect(redirect_url, 302)
        else:
            session['error'] = get_translate('errors.auth.bad_code_try')
            redirect_url = url_for('auth.code')
            return redirect(redirect_url, 307)
