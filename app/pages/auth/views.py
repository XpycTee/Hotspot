import re
import time
from hashlib import md5
from random import randint

from flask import render_template, request, current_app, redirect, url_for, session

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
async def check_authorization():
    if not session:
        session['chap-id'] = request.form.get('chap-id')
        session['chap-challenge'] = request.form.get('chap-challenge')
        session['link-login-only'] = request.form.get('link-login-only')
        session['link-orig'] = request.form.get('link-orig')
        session['mac'] = request.form.get('mac')

    mac = session.get('mac')

    db_client = models.WifiClient.query.filter_by(mac=mac).first()
    if db_client and int(time.time()) < db_client.expiration:
        username = current_app.config.get('HOTSPOT_USER')
        password = current_app.config.get('HOTSPOT_PASS')
        link_login_only = session.get('link-login-only').replace('https', 'http')
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
                link_login_only=link_login_only,
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
    phone_number = request.form.get('phone')
    phone_number = re.sub(r'^(\+?7|8)', '7', phone_number)
    phone_number = re.sub(r'\D', '', phone_number)

    gen_code = str(randint(1000, 9999))

    session['code'] = gen_code
    session['phone'] = phone_number

    # TODO use universal handler for sending sms messages
    print(f"{phone_number}: {gen_code} ваш код WiFi")

    return render_template('code.html')


@auth_bp.route('/auth', methods=['POST'])
async def auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    form_code = int(request.form.get('code'))
    user_code = int(session.get('code'))

    if form_code == user_code:
        db_client = models.WifiClient.query.filter_by(mac=mac).first()
        if not db_client:
            db_phone = models.ClientsNumber(phone_number=phone_number, last_seen=int(time.time()))
            db.session.add(db_phone)
            db.session.commit()
            db_client = models.WifiClient(mac=mac, expiration=int(time.time()), staff=False, phone_id=db_phone.id)
            db.session.add(db_client)
        db_client.expiration = int(time.time()) + 24*60*60  # 24 Hours
        db.session.commit()
    else:
        session['error'] = {"code": 400, "message": "Неверный код"}

    return redirect(url_for('auth.login'), 307)
