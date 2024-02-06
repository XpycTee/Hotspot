import datetime
import hashlib
import logging
import re
from hashlib import md5
from random import randint

import jmespath
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


@auth_bp.before_request
async def update_employees():
    employees_hash = current_app.config.get('EMP_HASH')
    with open("config/employees.yaml", "rb") as emp_config_file:
        file_contents = emp_config_file.read()
    new_hash = hashlib.md5(file_contents).hexdigest()
    if employees_hash != new_hash:
        current_app.config['EMPLOYEES'] = yaml.safe_load(file_contents).get('employees', [])
        current_app.config['EMP_HASH'] = new_hash


@auth_bp.before_request
async def check_authorization():
    if not session:
        session['chap-id'] = request.form.get('chap-id')
        session['chap-challenge'] = request.form.get('chap-challenge')
        session['link-login-only'] = request.form.get('link-login-only')
        session['link-orig'] = request.form.get('link-orig')
        session['mac'] = request.form.get('mac')

    mac = session.get('mac')

    db_client = models.WifiClient.query.filter_by(mac=mac).first()
    if db_client and datetime.datetime.now() < db_client.expiration:
        phone = db_client.phone
        phone_number = phone.phone_number
        is_employee = jmespath.search(f"[].phone | contains([], '{phone_number}')", current_app.config['EMPLOYEES'])

        username = 'employee' if is_employee else 'guest'
        password = current_app.config['HOTSPOT_USERS'][username].get('password')

        link_login_only = session.get('link-login-only')
        link_orig = session.get('link-orig')

        chap_id = session.get('chap-id')
        chap_challenge = session.get('chap-challenge')

        # use HTTP CHAP method in hotspot
        if chap_id and chap_challenge:
            chap_id = octal_string_to_bytes(chap_id)
            chap_challenge = octal_string_to_bytes(chap_challenge)

            pass_hash = md5(chap_id + password.encode() + chap_challenge).hexdigest()
            return render_template(
                'sendin.html',
                username=username,
                password=pass_hash,
                link_login_only=link_login_only.replace('https', 'http'),
                link_orig=link_orig
            )

        # use HTTPS method in hotspot
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
    phone_number = request.form.get('phone')
    if not phone_number:
        phone_number = session.get('phone')

    phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
    phone_number = re.sub(r'\D', '', phone_number)

    if phone_number in current_app.config['BLACKLIST']:
        abort(403)

    gen_code = str(randint(1000, 9999))

    session['code'] = gen_code
    session['phone'] = phone_number

    sender = current_app.config.get('SENDER')
    result = sender.send_sms(phone_number, current_app.config['LANGUAGE_CONTENT']['sms_code'].foramt(code=gen_code))
    if 'error' in result:
        abort(500)

    logging.debug(f"{phone_number}'s code: {gen_code}")

    return render_template('code.html', error=error)


@auth_bp.route('/auth', methods=['POST'])
async def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = int(request.form.get('code'))
    user_code = int(session.get('code'))

    is_employee = jmespath.search(f"[].phone | contains([], '{phone_number}')", current_app.config['EMPLOYEES'])

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

        delay: str = hotspot_user.get('delay')

        time_deltas = {
            'w': 'weeks',
            'd': 'days',
            'h': 'hours',
            'm': 'minutes',
            's': 'seconds'
        }
        suffix = delay[-1]
        if suffix.isdigit():
            db_client.expiration = now_time + datetime.timedelta(hours=int(delay))
        else:
            if suffix in time_deltas:
                amount = int(delay[:-1])
                db_client.expiration = now_time + datetime.timedelta(**{time_deltas[suffix]: amount})
            else:
                abort(500)

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
