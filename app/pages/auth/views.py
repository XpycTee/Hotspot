import datetime
import re
from functools import wraps
from hashlib import md5
from random import randint

import jmespath
import yaml
from flask import render_template, request, current_app, redirect, url_for, session, abort

from . import auth_bp
from ...database import models, db
import os


def octal_string_to_bytes(oct_string):
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


employee_cache = {
    'data': None,
    'last_modified': 0
}

def check_employee(phone_number):
    file_path = "config/employees.yaml"
    last_modified = os.path.getmtime(file_path)

    if employee_cache['data'] is None or last_modified > employee_cache['last_modified']:
        with open(file_path, "r", encoding="utf-8") as employees_file:
            employees = yaml.safe_load(employees_file)
            employee_cache['data'] = employees
            employee_cache['last_modified'] = last_modified

    expression = f"employees[].phone | contains([], '{phone_number}')"
    in_employees = bool(jmespath.search(expression, employee_cache['data']))
    return in_employees


def init_session(func):
    @wraps(func)
    def wrapped(*args):

        required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']

        if not all(key in request.form and request.form.get(key) for key in required_keys):
            abort(400)  # Raise a 400 error if any of the required keys is missing or empty

        session['chap-id'] = request.form.get('chap-id')
        session['chap-challenge'] = request.form.get('chap-challenge')
        session['link-login-only'] = request.form.get('link-login-only')
        session['link-orig'] = request.form.get('link-orig')
        session['mac'] = request.form.get('mac')

        return func(*args)
    return wrapped


def check_expiration(func):
    @wraps(func)
    def wrapped(*args):

        mac = session.get('mac')
        if not mac:
            abort(400)

        db_client = models.WifiClient.query.filter_by(mac=mac).first()
        if db_client and datetime.datetime.now() < db_client.expiration:
            phone = db_client.phone
            if not phone:
                abort(500)

            phone_number = phone.phone_number
            is_employee = check_employee(phone_number)

            username = 'employee' if is_employee else 'guest'
            password = current_app.config['HOTSPOT_USERS'][username].get('password')
            if not password:
                abort(500)

            link_login_only = session.get('link-login-only')
            link_orig = session.get('link-orig')

            chap_id = session.get('chap-id')
            chap_challenge = session.get('chap-challenge')

            session.clear()
            # use HTTP CHAP method in hotspot
            if chap_id and chap_challenge:
                chap_id = octal_string_to_bytes(chap_id)
                chap_challenge = octal_string_to_bytes(chap_challenge)
                link_login_only = link_login_only.replace('https', 'http')
                password = md5(chap_id + password.encode() + chap_challenge).hexdigest()

            return render_template(
                'sendin.html',
                username=username,
                password=password,
                link_login_only=link_login_only,
                link_orig=link_orig
            )

        return func(*args)
    return wrapped


@auth_bp.route('/login', methods=['POST'])
@init_session
@check_expiration
def login():
    error = session.pop('error', None)
    return render_template('login.html', error=error)  # Form send phone to /CODE


@auth_bp.route('/code', methods=['POST'])
@check_expiration
def code():
    error = session.pop('error', None)

    phone_number = request.form.get('phone')
    if not phone_number:
        abort(400)
        
    phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
    phone_number = re.sub(r'\D', '', phone_number)

    if phone_number in current_app.config['BLACKLIST']:
        abort(403)

    session['phone'] = phone_number

    mac = session.get('mac')
    if not mac:
        abort(400)

    db_client = models.WifiClient.query.filter_by(mac=mac).first()

    if db_client and db_client.phone and db_client.phone.phone_number == phone_number:
        is_employee = check_employee(phone_number)

        users_config = current_app.config['HOTSPOT_USERS']

        hotspot_user = users_config['employee'] if is_employee else users_config['guest']

        now_time = datetime.datetime.now()

        db_client.expiration = now_time + hotspot_user.get('delay')
        db_client.employee = is_employee
        db.session.commit()

    if 'code' not in session:

        gen_code = str(randint(0, 9999)).zfill(4)
        session['code'] = gen_code

        sender = current_app.config.get('SENDER')
        sms_error = sender.send_sms(phone_number, current_app.config['LANGUAGE_CONTENT']['sms_code'].format(code=gen_code))

        if sms_error:
            abort(500)

        current_app.logger.debug(f"{phone_number}'s code: {gen_code}")

    return render_template('code.html', error=error)


@auth_bp.route('/auth', methods=['POST'])
@check_expiration
def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = request.form.get('code')
    user_code = session.get('code')

    if form_code is None or user_code is None:
        session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['missing_code']
        redirect_url = url_for('auth.code')
        return redirect(redirect_url, 307)


    form_code = int(form_code)
    user_code = int(user_code)

    if form_code == user_code:
        now_time = datetime.datetime.now()

        db_phone = models.ClientsNumber.query.filter_by(phone_number=phone_number).first()
        if not db_phone:
            db_phone = models.ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db.session.add(db_phone)
            db.session.commit()
        
        is_employee = check_employee(phone_number)

        db_client = models.WifiClient.query.filter_by(mac=mac).first()
        if not db_client:
            db_client = models.WifiClient(mac=mac, expiration=now_time, employee=is_employee, phone=db_phone)
            db.session.add(db_client)
        else:
            db_client.phone = db_phone
            db_client.expiration = now_time
            db_client.employee = is_employee

        users_config = current_app.config['HOTSPOT_USERS']
        hotspot_user = users_config['employee'] if is_employee else users_config['guest']

        delay = hotspot_user.get('delay')
        db_client.expiration = now_time + delay

        db.session.commit()

        session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_auth']
        redirect_url = url_for('auth.auth')
        return redirect(redirect_url, 307)
    else:
        session.setdefault('tries', 0)
        session['tries'] += 1

        if session['tries'] >= 3:
            session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_code_all']
            session.pop('code')  # Remove code from session for generating new when tries end

            redirect_url = url_for('auth.auth')
            return redirect(redirect_url, 307)
        else:
            session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_code_try']
            redirect_url = url_for('auth.code')
            return redirect(redirect_url, 307)

