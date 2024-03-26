import datetime
import logging
import re
from hashlib import md5
from random import randint

import jmespath
import requests
import yaml
from flask import render_template, request, current_app, redirect, url_for, session, abort

from . import auth_bp
from ...database import models, db


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


def check_employee(phone_number):
    with requests.get('https://is.sova72.ru/documents/employee/phonebook.json') as response:
        employees = response.json()
        expression = f"employee[].phone[].number | contains([], '{phone_number}')"
        in_base = bool(jmespath.search(expression, employees))
    if not in_base:
        with open("config/employees.yaml", "r", encoding="utf-8") as employees_file:
            employees = yaml.safe_load(employees_file)
            expression = f"employees[].phone[] | contains([], '{phone_number}')"
            in_employees = bool(jmespath.search(expression, employees))
        return in_employees
    return in_base


@auth_bp.before_request
async def init_session():
    required_keys = ['chap-id', 'chap-challenge', 'link-login-only', 'link-orig', 'mac']

    if not all(key in request.form for key in required_keys):
        abort(400)  # Raise a 400 error if any of the required keys is missing

    session['chap-id'] = request.form.get('chap-id')
    session['chap-challenge'] = request.form.get('chap-challenge')
    session['link-login-only'] = request.form.get('link-login-only')
    session['link-orig'] = request.form.get('link-orig')
    session['mac'] = request.form.get('mac')


@auth_bp.before_request
async def check_authorization():
    if 'phone' in request.form:
        phone_number = request.form.get('phone')
        if not phone_number:
            phone_number = session.get('phone')

        phone_number = re.sub(r'^(\+?7|8)', '', phone_number)
        phone_number = re.sub(r'\D', '', phone_number)

        if phone_number in current_app.config['BLACKLIST']:
            abort(403)

        session['phone'] = phone_number

        mac = session.get('mac')
        db_client = models.WifiClient.query.filter_by(mac=mac).first()
        if db_client and db_client.phone.phone_number == phone_number:
            users_config = current_app.config['HOTSPOT_USERS']
            is_employee = check_employee(phone_number)
            hotspot_user = users_config['employee'] if is_employee else users_config['guest']

            now_time = datetime.datetime.now()

            db_client.expiration = now_time + hotspot_user.get('delay')
            db_client.employee = is_employee
            db.session.commit()


@auth_bp.before_request
async def check_registration():
    mac = session.get('mac')

    db_client = models.WifiClient.query.filter_by(mac=mac).first()
    if db_client and datetime.datetime.now() < db_client.expiration:
        phone = db_client.phone
        phone_number = phone.phone_number

        username = 'employee' if check_employee(phone_number) else 'guest'
        password = current_app.config['HOTSPOT_USERS'][username].get('password')

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


@auth_bp.route('/login', methods=['POST'])
async def login():
    error = session.pop('error', None)
    return render_template('login.html', error=error)


@auth_bp.route('/code', methods=['POST'])
async def code():
    error = session.pop('error', None)
    phone_number = session.get('phone')

    if 'code' not in session:

        gen_code = str(randint(0, 9999)).zfill(4)
        session['code'] = gen_code
        session['phone'] = phone_number

        sender = current_app.config.get('SENDER')
        result = sender.send_sms(phone_number, current_app.config['LANGUAGE_CONTENT']['sms_code'].format(code=gen_code))

        if result:
            abort(500)

        logging.debug(f"{phone_number}'s code: {gen_code}")

    return render_template('code.html', error=error)


@auth_bp.route('/auth', methods=['POST'])
async def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = int(request.form.get('code'))
    user_code = int(session.get('code'))

    is_employee = check_employee(phone_number)

    if form_code == user_code:
        db_client = models.WifiClient.query.filter_by(mac=mac).first()
        now_time = datetime.datetime.now()
        if not db_client:
            db_phone = models.ClientsNumber(phone_number=phone_number, last_seen=now_time)
            db.session.add(db_phone)
            db.session.commit()
            db_client = models.WifiClient(mac=mac, expiration=now_time, employee=is_employee, phone=db_phone)
            db.session.add(db_client)

        users_config = current_app.config['HOTSPOT_USERS']
        hotspot_user = users_config['employee'] if is_employee else users_config['guest']

        delay = hotspot_user.get('delay')
        db_client.expiration = now_time + delay

        db.session.commit()

        session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_auth']
        return redirect(url_for('auth.login'), 307)
    else:
        session.setdefault('tries', 0)
        session['tries'] += 1

        if session['tries'] >= 3:
            session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_code_all']
            session.pop('code')  # Remove code from session

            return redirect(url_for('auth.login'), 307)
        else:
            session['error'] = current_app.config['LANGUAGE_CONTENT']['errors']['auth']['bad_code_try']
            return redirect(url_for('auth.code'), 307)
