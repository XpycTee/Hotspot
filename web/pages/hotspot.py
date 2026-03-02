import random
import secrets
import string
import time
import json

from flask import Blueprint, jsonify, render_template, redirect, url_for, abort, session, request, current_app, Response

from core.hotspot.authorization.service import Authorization, AuthStatus
from core.hotspot.verification.service import Verification, VerificationStatus
from core.utils.language import get_translate
from core.utils.phone import normalize_phone

from core.hotspot.wifi.auth import get_credentials

import web.logger as logger

hotspot_bp = Blueprint('hotspot', __name__)


def _mask_phone(phone: str) -> str:
    return '*'*(len(phone)-4) + phone[-4:]


def _mask_mac(mac: str) -> str:
    parts = mac.split(':')
    return 'XX:XX:XX:' + ':'.join(parts[3:])


def _log_masked_session():
    sensetive = ["chap-id", "chap-challenge", "password"]
    result = {}
    items = session.items()
    for k, v in items:
        if k.startswith("_"):
            continue
        if k == "phone":
            result[k] = _mask_phone(v)
        elif k == "mac":
            result[k] = _mask_mac(v)
        elif k in ["hardware_fp", "user_fp"]:
            result[k] = v[:12]
        elif k in sensetive:
            result[k] = '******'
        else:
            result[k] = v

    return result


def _get_verify_session_id() -> str:
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        verify_session_id = secrets.token_urlsafe(24)
        session['verify_session_id'] = verify_session_id
    return verify_session_id


def _get_call_verification_payload(verify_session_id: str) -> dict:
    service = Verification(verify_session_id)
    response = service.call_verification()

    if response.status == VerificationStatus.WAIT_CALL:
        return {'state': 'pending'}

    if response.status == VerificationStatus.TIMEOUT:
        return {'state': 'timeout', 'message': response.error_message}

    if response.status in [VerificationStatus.FAILED, VerificationStatus.ERROR]:
        return {'state': 'failed', 'message': response.error_message}

    if response.status == VerificationStatus.VERIFIED:
        return {'state': 'verified'}

    return {'state': 'failed'}


@hotspot_bp.route('/', methods=['POST', 'GET'])
def index():
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    if not has_form and not has_session:
        if 'link-orig' not in session.keys():
            abort(400)
        else:
            return redirect(session.get('link-orig'), 302)

    return redirect(url_for('pages.hotspot.login'), 302)


@hotspot_bp.route('/test', methods=['GET'])
def test():
    if not current_app.debug:
        abort(404)

    characters = string.ascii_letters + string.digits
    mac = "02:00:00:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    hardware_fp = "".join(secrets.choice(characters) for _ in range(12))

    gen_request = {
        'mac': request.values.get('mac', mac),
        'link-orig': request.values.get('link-orig', 'http://test.lan:81/orig'),
        'link-login-only': request.values.get('link-login-only', 'http://test.lan:81/test'),
        'hardware_fp': request.values.get('hardware_fp', hardware_fp),
    }

    [session.update({k: v}) for k, v in gen_request.items()]
    logger.debug(f'Session data in test: {_log_masked_session()}')
    return login()


@hotspot_bp.route('/login', methods=['POST'])
def login():
    error = session.pop('error', None)

    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    logger.debug(f'Session data before form: {_log_masked_session()}')

    if not has_form and not has_session:
        abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]

    logger.debug(f'Session data after form: {_log_masked_session()}')
    mac = session.get('mac')
    hardware_fp = session.get('hardware_fp')

    auth_service = Authorization()
    response = auth_service.mac_authorization(mac, hardware_fp)

    if response.status == AuthStatus.AUTHORIZED:
        session['phone'] = response.phone
        session['user_fp'] = response.user_fp
        return redirect(url_for('pages.hotspot.sendin'), 302)
    if response.status == AuthStatus.BLOCKED:
        abort(403)
    if response.status == AuthStatus.FAILED:
        return render_template(
            'hotspot/login.html', 
            error=response.error_message,
        )
    
    abort(500)


@hotspot_bp.route('/preauth', methods=['POST'])
def preauth():
    logger.debug(f'Session data before code: {_log_masked_session()}')

    form_phone = request.form.get('phone')
    norm_phone = normalize_phone(form_phone)
    session['phone'] = norm_phone

    mac = session.get('mac')
    hardware_fp = session.get('hardware_fp')

    auth_service = Authorization()
    auth_response = auth_service.phone_authorization(mac, norm_phone, hardware_fp)
    if auth_response.status == AuthStatus.BLOCKED:
        abort(403)
    
    session['user_fp'] = auth_response.user_fp
    if auth_response.status == AuthStatus.AUTHORIZED:
        return redirect(url_for('pages.hotspot.sendin'), 302)
    
    if auth_response.status == AuthStatus.FAILED:
        verify_service = Verification(_get_verify_session_id())

        verify_response = verify_service.start_verification(norm_phone)
        if verify_response.status == VerificationStatus.WAIT_CALL:
            return render_template(
                'hotspot/callcheck.html', 
                call_phone=verify_response.call_phone, 
                code_avail=verify_response.code_avail,
            )
        if verify_response.status == VerificationStatus.SENDING_CODE:
            return redirect(url_for('pages.hotspot.code_send'), 302)
    
    abort(500)


@hotspot_bp.route('/code/send', methods=['POST', 'GET'])
def code_send():
    error = session.pop('error', None)
    logger.debug(f'Session data before code: {_log_masked_session()}')

    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        abort(400)

    service = Verification(verify_session_id)
    response = service.send_code()

    if response.status in (VerificationStatus.FAILED, VerificationStatus.ERROR):
        return render_template(
            'hotspot/code.html', 
            error=response.error_message,
        )

    if response.status == VerificationStatus.WAIT_CODE:
        return render_template('hotspot/code.html', error=error)
    
    abort(500)


@hotspot_bp.route('/code/resend', methods=['POST'])
def resend():
    phone_number = session.get('phone')
    logger.debug(f'Session data before code: {_log_masked_session()}')
    if not phone_number:
        abort(400)

    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        abort(400)

    service = Verification(verify_session_id)
    response = service.send_code()

    if response.status in (VerificationStatus.FAILED, VerificationStatus.ERROR):
        return jsonify({'success': False, 'error_message': response.error_message})

    if response.status == VerificationStatus.WAIT_CODE:
        return jsonify({'success': True})

    abort(500)


@hotspot_bp.route('/code/auth', methods=['POST'])
def code_auth():
    user_fp = session.get('user_fp')
    verify_session_id = session.get('verify_session_id')
    form_code = request.form.get('code')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        return redirect(url_for('pages.hotspot.code_send'), 302)

    if not verify_session_id:
        abort(400)

    verify_service = Verification(verify_session_id)
    verify_response = verify_service.code_verification(form_code)

    if verify_response.status == VerificationStatus.FAILED:
        session['error'] = verify_response.error_message
        return redirect(url_for('pages.hotspot.code_send'), 302)
    
    if verify_response.status == VerificationStatus.RETRY:
        session['error'] = verify_response.error_message
        return redirect(url_for('pages.hotspot.code_send'), 307)
    
    if verify_response.status == VerificationStatus.DENIED:
        session['error'] = verify_response.error_message
        session.pop('phone', None)
        session.pop('verify_session_id', None)
        return redirect(url_for('pages.hotspot.login'), 302)
    
    if verify_response.status == VerificationStatus.VERIFIED:
        session.pop('verify_session_id', None)
        mac = session.get('mac')
        phone = session.get('phone')

        auth_service = Authorization()
        auth_response = auth_service.authorization(mac, phone, user_fp)
        if auth_response.status == AuthStatus.BLOCKED:
            abort(403)
        if auth_response.status == AuthStatus.AUTHORIZED:
            return redirect(url_for('pages.hotspot.sendin'), 302)
        if auth_response.status == AuthStatus.FAILED:
            session['error'] = auth_response.error_message
            session.pop('phone', None)
            return redirect(url_for('pages.hotspot.login'), 302)
    
    abort(500)


@hotspot_bp.route('/call/check/poll', methods=['GET'])
def call_check_poll():
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        abort(400)

    payload = _get_call_verification_payload(verify_session_id)
    if payload.get('state') == 'verified':
        session.pop('verify_session_id', None)
    return jsonify(payload)


@hotspot_bp.route('/call/check/stream', methods=['GET'])
def call_check_stream():
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        abort(400)

    poll_interval_seconds = 2

    def event_stream():
        # Let EventSource know preferred reconnection delay in milliseconds.
        yield "retry: 3000\n\n"

        while True:
            payload = _get_call_verification_payload(verify_session_id)

            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if payload['state'] != 'pending':
                break

            time.sleep(poll_interval_seconds)

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return Response(event_stream(), mimetype='text/event-stream', headers=headers)


@hotspot_bp.route('/call/auth', methods=['POST', 'GET'])
def call_auth():
    mac = session.get('mac')
    phone = session.get('phone')
    user_fp = session.get('user_fp')
    if not mac or not phone or not user_fp:
        abort(400)

    auth_service = Authorization()
    auth_response = auth_service.authorization(mac, phone, user_fp)
    if auth_response.status == AuthStatus.BLOCKED:
        abort(403)
    if auth_response.status == AuthStatus.AUTHORIZED:
        return redirect(url_for('pages.hotspot.sendin'), 302)
    if auth_response.status == AuthStatus.FAILED:
        session['error'] = auth_response.error_message
        session.pop('phone', None)
        session.pop('verify_session_id', None)
        return redirect(url_for('pages.hotspot.login'), 302)

    abort(500)


@hotspot_bp.route('/sendin', methods=['POST', 'GET'])
def sendin():
    phone_number = session.get('phone')
    if not phone_number:
        abort(400)

    link_login_only = session.get('link-login-only')
    link_orig = session.get('link-orig')
    chap_id = session.get('chap-id')
    chap_challenge = session.get('chap-challenge')
    mac = session.get('mac')
    user_fp = session.get('user_fp')
    session.clear()

    auth_service = Authorization()

    if not auth_service.authorized(user_fp):
        abort(401)

    if chap_id and chap_challenge:
        link_login_only = link_login_only.replace('https', 'http')

    credentials = get_credentials(mac, phone_number, user_fp, chap_id, chap_challenge)
    username = credentials.get('username')
    password = credentials.get('password')

    return render_template(
        'hotspot/sendin.html', 
        username=username,
        password=password,
        link_login_only=link_login_only,
        link_orig=link_orig
    )
