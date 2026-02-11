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

from core.hotspot.auth.callcheck import add_phone, check_phone
from core.hotspot.auth.code import send_code
from core.hotspot.auth.confirm import check_confirm
from core.utils.language import get_translate
from core.utils.phone import normalize_phone
from core.hotspot.wifi.auth import authenticate_by_mac, authenticate_by_phone

from core.hotspot.wifi.auth import authenticate_by_code
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


@hotspot_bp.route('/', methods=['POST', 'GET'])
def index():
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    if not has_form and not has_session:
        if 'link-orig' not in session.keys():
            abort(400)
        else:
            redirect(session.get('link-orig'), 302)

    return redirect(url_for('pages.hotspot.login'), 302)


@hotspot_bp.route('/test_login', methods=['GET'])
def test_login():
    if not current_app.debug:
        abort(404)
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_requirements = all(key in set(request.values.keys()) for key in required_keys)
    if not has_requirements:
        abort(400)
    else:
        [session.update({k: v}) for k, v in request.values.items()]
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

    response = authenticate_by_mac(mac, hardware_fp)

    status = response.get('status')
    if status == "OK":
        phone = response.get('phone')
        user_fp = response.get('user_fp')

        session['phone'] = phone
        if user_fp:
            session['user_fp'] = user_fp

        return redirect(url_for('pages.hotspot.sendin'), 302)
    elif status == "BLOCKED":
        abort(403)
    elif status in ["NOT_FOUND", "EXPIRED"]:
        return render_template('hotspot/login.html', error=error)
    else:
        abort(500)


@hotspot_bp.route('/preauth', methods=['POST'])
def preauth():
    logger.debug(f'Session data before code: {_log_masked_session()}')

    method = request.form.get('method')
    phone_number = request.form.get('phone')
    phone_number = normalize_phone(phone_number)

    mac = session.get('mac')
    hardware_fp = session.get('hardware_fp')

    session['phone'] = phone_number

    response = authenticate_by_phone(mac, phone_number, hardware_fp)
    status = response.get('status')
    if status == "OK":
        session['user_fp'] = response.get('user_fp')
        return redirect(url_for('pages.hotspot.sendin'), 302)
    
    if status == "BLOCKED":
        abort(403)

    if status == 'NOT_FOUND':
        logger.debug('User not found. Continue...')
        if method == 'code':
            return redirect(url_for('pages.hotspot.code_send'), 302)
        elif method == 'callcheck':
            return redirect(url_for('pages.hotspot.call_add'), 302)
        else:
            abort(400)

    abort(500)


@hotspot_bp.route('/code/send', methods=['POST', 'GET'])
def code_send():
    error = session.pop('error', None)
    logger.debug(f'Session data before code: {_log_masked_session()}')
    phone_number = request.form.get('phone')

    if not phone_number:
        phone_number = session.get('phone')
        logger.debug(f'User phone from session: {_mask_phone(phone_number)}')
        if not phone_number:
            abort(400)

    user_fp = session.get('user_fp')

    response = send_code(user_fp, phone_number)

    status = response.get('status')
    if status == "OK":
        return render_template('hotspot/code.html', error=error)
    if status == "ALREDY_SENDED":
        error_message = response.get('error_message')
        return render_template('hotspot/code.html', error=error_message)
    if status == "SENDER_ERROR":
        return render_template('hotspot/code.html', error='Sender error')
    abort(500)


@hotspot_bp.route('/code/resend', methods=['POST'])
def code_resend():
    phone_number = session.get('phone')
    logger.debug(f'Session data before code: {_log_masked_session()}')
    if not phone_number:
        abort(400)
    
    user_fp = session.get('user_fp')
    response = send_code(user_fp, phone_number)
    status = response.get('status')
    if status == "OK":
        return jsonify({'success': True})
    if status == "ALREDY_SENDED":
        error_message = response.get('error_message')
        abort(400, description=error_message)
    if status == "SENDER_ERROR":
        return jsonify({'success': False, 'error_message': 'Sender error'})
    abort(500)


@hotspot_bp.route('/code/auth', methods=['POST'])
def code_auth():
    mac = session.get('mac')
    phone_number = session.get('phone')
    if not mac or not phone_number:
        abort(400)

    user_fp = session.get('user_fp')
    form_code = request.form.get('code')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        return redirect(url_for('pages.hotspot.code_send'), 302)

    response = authenticate_by_code(user_fp, mac, form_code, phone_number)
    status = response.get('status')
    if status == "OK":
        return redirect(url_for('pages.hotspot.sendin'), 302)

    session['error'] = response.get('error_message')
    if status == "CODE_EXPIRED":
        return redirect(url_for('pages.hotspot.code_send'), 302)
    if status == "BAD_TRY":
        return redirect(url_for('pages.hotspot.code_send'), 307)
    if status == "BAD_CODE":
        session.pop('phone', None)
        return redirect(url_for('pages.hotspot.login'), 302)
    
    abort(500)


@hotspot_bp.route('/call/add', methods=['POST', 'GET'])
def call_add():
    error = session.pop('error', None)
    logger.debug(f'Session data before code: {_log_masked_session()}')
    phone_number = request.form.get('phone')

    if not phone_number:
        phone_number = session.get('phone')
        logger.debug(f'User phone from session: {_mask_phone(phone_number)}')
        if not phone_number:
            abort(400)

    user_fp = session.get('user_fp')

    response = add_phone(user_fp, phone_number)

    status = response.get('status')
    if status == "OK":
        return render_template('hotspot/callcheck.html', error=error)
    if status == "ALREDY_SENDED":
        error_message = response.get('error_message')
        return render_template('hotspot/callcheck.html', error=error_message)
    else:
        abort(500)


@hotspot_bp.route('/call/check', methods=['POST'])
def call_check():
    phone_number = session.get('phone')
    logger.debug(f'Session data before code: {_log_masked_session()}')
    if not phone_number:
        abort(400)
    
    user_fp = session.get('user_fp')

    response = check_phone(user_fp, phone_number)
    status = response.get('status')
    if status == "OK":
        return jsonify({'success': True}, 200)
    if status == "NOT_AUTH":
        return jsonify({'success': False, 'message': 'Not auth'}, 200)
    if status == "TIMEOUT":
        return jsonify({'success': False, 'message': 'Timeout'}, 408)
    if status == "ERROR":
        return jsonify({'success': False, 'error_message': 'Callcheck error'}, 500)
    
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

    if not check_confirm(user_fp):
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

