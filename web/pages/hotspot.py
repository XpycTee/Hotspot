import json
import random
import secrets
import string
import time
from typing import Any

from flask import Blueprint, Response, abort, current_app, has_request_context, jsonify, redirect, render_template, request, session, url_for

from core.hotspot.authorization.service import AuthFailReason, AuthStatus, Authorization
from core.hotspot.verification.service import Verification, VerificationStatus
from core.hotspot.wifi.auth import get_credentials
from core.utils.language import get_translate
from core.utils.phone import normalize_phone

import web.logger as logger

hotspot_bp = Blueprint('hotspot', __name__)


def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    if len(phone) <= 4:
        return '*' * len(phone)
    return '*' * (len(phone) - 4) + phone[-4:]


def _mask_mac(mac: str | None) -> str | None:
    if not mac:
        return None
    parts = mac.split(':')
    if len(parts) < 6:
        return 'XX:XX:XX'
    return 'XX:XX:XX:' + ':'.join(parts[3:])


def _log_masked_session() -> dict[str, Any]:
    sensitive = ["chap-id", "chap-challenge", "password"]
    result: dict[str, Any] = {}
    for k, v in session.items():
        if k.startswith("_"):
            continue
        if k == "phone":
            result[k] = _mask_phone(v)
        elif k == "mac":
            result[k] = _mask_mac(v)
        elif k in ["hardware_fp", "user_fp"] and isinstance(v, str):
            result[k] = v[:12]
        elif k in sensitive:
            result[k] = '******'
        else:
            result[k] = v

    return result


def _get_auth_flow_id() -> str:
    auth_flow_id = session.get('auth_flow_id')
    if not auth_flow_id:
        auth_flow_id = secrets.token_urlsafe(16)
        session['auth_flow_id'] = auth_flow_id
    return auth_flow_id


def _get_verify_session_id() -> str:
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        verify_session_id = secrets.token_urlsafe(24)
        session['verify_session_id'] = verify_session_id
    return verify_session_id


def _build_flow_ctx(
    stage: str,
    verify_session_id: str | None = None,
    base_ctx: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx: dict[str, Any] = dict(base_ctx or {})
    if 'auth_flow_id' not in ctx:
        ctx['auth_flow_id'] = session.get('auth_flow_id') if has_request_context() else None
    if 'verify_session_id' not in ctx:
        ctx['verify_session_id'] = verify_session_id or (session.get('verify_session_id') if has_request_context() else None)
    elif verify_session_id is not None:
        ctx['verify_session_id'] = verify_session_id
    if 'route' not in ctx:
        ctx['route'] = request.endpoint if has_request_context() else None
    ctx['stage'] = stage
    for key, value in kwargs.items():
        if value is not None:
            ctx[key] = value
    return ctx


def _flow_prefix(ctx: dict[str, Any]) -> str:
    auth_flow = ctx.get('auth_flow_id') or '-'
    verify_flow = ctx.get('verify_session_id') or '-'
    stage = ctx.get('stage') or '-'
    return f'[auth_flow={auth_flow} verify={verify_flow} stage={stage}]'


def _flow_log(
    level: str,
    message: str,
    stage: str,
    verify_session_id: str | None = None,
    base_ctx: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = _build_flow_ctx(stage, verify_session_id=verify_session_id, base_ctx=base_ctx, **kwargs)
    log_fn = getattr(logger, level)
    log_fn(f'{_flow_prefix(ctx)} {message}', extra=ctx)
    return ctx


def _get_call_verification_payload(verify_session_id: str, base_ctx: dict[str, Any] | None = None) -> dict:
    service = Verification(
        verify_session_id,
        flow_ctx=_build_flow_ctx('call.check', verify_session_id=verify_session_id, base_ctx=base_ctx),
    )
    response = service.call_verification()

    if response.status == VerificationStatus.WAIT_CALL:
        _flow_log(
            'debug',
            'Call verification still pending',
            'call.check',
            verify_session_id=verify_session_id,
            base_ctx=base_ctx,
            event='verify.call.poll',
            status=response.status.name,
        )
        return {'state': 'pending'}

    if response.status == VerificationStatus.TIMEOUT:
        _flow_log(
            'warning',
            f'Call verification timeout: {response.error_message}',
            'call.check',
            verify_session_id=verify_session_id,
            base_ctx=base_ctx,
            event='verify.call.poll',
            status=response.status.name,
        )
        return {'state': 'timeout', 'message': response.error_message}

    if response.status in [VerificationStatus.FAILED, VerificationStatus.ERROR]:
        _flow_log(
            'error',
            f'Call verification failed: {response.error_message}',
            'call.check',
            verify_session_id=verify_session_id,
            base_ctx=base_ctx,
            event='verify.call.poll',
            status=response.status.name,
        )
        return {'state': 'failed', 'message': response.error_message}

    if response.status == VerificationStatus.VERIFIED:
        _flow_log(
            'info',
            'Call verification completed',
            'call.check',
            verify_session_id=verify_session_id,
            base_ctx=base_ctx,
            event='verify.call.poll',
            status=response.status.name,
        )
        return {'state': 'verified'}

    _flow_log(
        'error',
        f'Unexpected call verification response: {response}',
        'call.check',
        verify_session_id=verify_session_id,
        base_ctx=base_ctx,
        event='verify.call.poll',
        status=response.status.name,
    )
    return {'state': 'failed'}


@hotspot_bp.route('/', methods=['POST', 'GET'])
def index():
    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    if not has_form and not has_session:
        if 'link-orig' not in session.keys():
            abort(400)
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

    for k, v in gen_request.items():
        session.update({k: v})

    _get_auth_flow_id()
    _flow_log(
        'debug',
        f'Session data in test: {_log_masked_session()}',
        'test',
        event='auth.flow.start',
    )
    return login()


@hotspot_bp.route('/login', methods=['POST'])
def login():
    error = session.pop('error', None)
    _get_auth_flow_id()

    required_keys = ['link-login-only', 'link-orig', 'mac']
    has_form = all(key in set(request.form.keys()) for key in required_keys)
    has_session = all(key in set(session.keys()) for key in required_keys)

    _flow_log(
        'info',
        'Hotspot login started',
        'login',
        event='auth.flow.start',
        has_form=has_form,
        has_session=has_session,
    )
    _flow_log('debug', f'Session data before form: {_log_masked_session()}', 'login', event='auth.flow.start')

    if not has_form and not has_session:
        _flow_log('warning', 'Bad login request payload', 'login', event='auth.flow.start')
        abort(400)

    for k, v in request.values.items():
        session.update({k: v})

    _flow_log('debug', f'Session data after form: {_log_masked_session()}', 'login', event='auth.flow.start')
    mac = session.get('mac')

    auth_service = Authorization()
    flow_ctx = _build_flow_ctx('login', event='auth.mac.check')
    response = auth_service.mac_authorization(mac, flow_ctx=flow_ctx)
    _flow_log(
        'debug',
        f'MAC authorization result: {response.status.name}',
        'login',
        event='auth.mac.check',
        status=response.status.name,
        fail_reason=response.fail_reason.name if response.fail_reason else None,
        mac=_mask_mac(mac),
    )

    if response.status == AuthStatus.AUTHORIZED:
        session['phone'] = response.phone
        session['user_fp'] = response.user_fp
        _flow_log('info', 'Flow authorized by MAC and redirected to sendin', 'login', event='auth.flow.end', status='AUTHORIZED')
        return redirect(url_for('pages.hotspot.sendin'), 302)
    if response.status == AuthStatus.BLOCKED:
        _flow_log('warning', 'MAC authorization blocked', 'login', event='auth.mac.check', status='BLOCKED')
        abort(403)
    if response.status == AuthStatus.FAILED:
        if response.fail_reason == AuthFailReason.NOT_FOUND:
            _flow_log('info', 'MAC not found, showing login form', 'login', event='auth.mac.check', status='FAILED')
            return render_template('hotspot/login.html', error=None)

        _flow_log('warning', 'MAC authorization failed', 'login', event='auth.mac.check', status='FAILED')
        return render_template(
            'hotspot/login.html',
            error=response.error_message,
        )

    _flow_log('error', 'Unexpected status from MAC authorization', 'login', event='auth.mac.check')
    abort(500)


@hotspot_bp.route('/preauth', methods=['POST'])
def preauth():
    _get_auth_flow_id()
    _flow_log('debug', f'Session data before preauth: {_log_masked_session()}', 'preauth', event='auth.phone.check')

    form_phone = request.form.get('phone')
    norm_phone = normalize_phone(form_phone)
    session['phone'] = norm_phone

    mac = session.get('mac')
    hardware_fp = session.get('hardware_fp')

    auth_service = Authorization()
    auth_response = auth_service.phone_authorization(
        mac,
        norm_phone,
        hardware_fp,
        flow_ctx=_build_flow_ctx('preauth', event='auth.phone.check', phone=_mask_phone(norm_phone)),
    )
    _flow_log(
        'debug',
        f'Phone authorization result: {auth_response.status.name}',
        'preauth',
        event='auth.phone.check',
        status=auth_response.status.name,
        fail_reason=auth_response.fail_reason.name if auth_response.fail_reason else None,
        phone=_mask_phone(norm_phone),
    )

    if auth_response.status == AuthStatus.BLOCKED:
        _flow_log('warning', 'Phone authorization blocked', 'preauth', event='auth.phone.check', status='BLOCKED')
        abort(403)

    if auth_response.status == AuthStatus.AUTHORIZED:
        session['user_fp'] = auth_response.user_fp
        _flow_log('info', 'Phone authorization successful, redirecting to sendin', 'preauth', event='auth.flow.end', status='AUTHORIZED')
        return redirect(url_for('pages.hotspot.sendin'), 302)

    if auth_response.status == AuthStatus.FAILED:
        verify_session_id = _get_verify_session_id()
        verify_service = Verification(
            verify_session_id,
            flow_ctx=_build_flow_ctx('preauth', verify_session_id=verify_session_id, event='verify.start'),
        )

        verify_response = verify_service.start_verification(norm_phone)
        _flow_log(
            'debug',
            f'Verification start result: {verify_response.status.name}',
            'preauth',
            verify_session_id=verify_session_id,
            event='verify.start',
            status=verify_response.status.name,
        )
        if verify_response.status == VerificationStatus.WAIT_CALL:
            return render_template(
                'hotspot/callcheck.html',
                call_phone=verify_response.call_phone,
                code_avail=verify_response.code_avail,
            )
        if verify_response.status == VerificationStatus.SENDING_CODE:
            return redirect(url_for('pages.hotspot.code_send'), 302)

    _flow_log('error', 'Unexpected preauth result', 'preauth', event='auth.phone.check')
    abort(500)


@hotspot_bp.route('/code/send', methods=['POST', 'GET'])
def code_send():
    error = session.pop('error', None)
    _flow_log('debug', f'Session data before code_send: {_log_masked_session()}', 'code.send', event='verify.code.send')

    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        _flow_log('warning', 'Missing verify_session_id in code_send', 'code.send', event='verify.code.send')
        abort(400)

    service = Verification(
        verify_session_id,
        flow_ctx=_build_flow_ctx('code.send', verify_session_id=verify_session_id, event='verify.code.send'),
    )
    response = service.send_code()
    _flow_log(
        'debug',
        f'Code send result: {response.status.name}',
        'code.send',
        verify_session_id=verify_session_id,
        event='verify.code.send',
        status=response.status.name,
    )

    if response.status in (VerificationStatus.FAILED, VerificationStatus.ERROR):
        return render_template(
            'hotspot/code.html',
            error=response.error_message,
        )

    if response.status == VerificationStatus.WAIT_CODE:
        return render_template('hotspot/code.html', error=error)

    _flow_log('error', 'Unexpected code_send status', 'code.send', verify_session_id=verify_session_id, event='verify.code.send')
    abort(500)


@hotspot_bp.route('/code/resend', methods=['POST'])
def resend():
    phone_number = session.get('phone')
    _flow_log('debug', f'Session data before code_resend: {_log_masked_session()}', 'code.resend', event='verify.code.send')
    if not phone_number:
        _flow_log('warning', 'Missing phone in code_resend', 'code.resend', event='verify.code.send')
        abort(400)

    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        _flow_log('warning', 'Missing verify_session_id in code_resend', 'code.resend', event='verify.code.send')
        abort(400)

    service = Verification(
        verify_session_id,
        flow_ctx=_build_flow_ctx('code.resend', verify_session_id=verify_session_id, event='verify.code.send'),
    )
    response = service.send_code()

    if response.status in (VerificationStatus.FAILED, VerificationStatus.ERROR):
        _flow_log('warning', 'Code resend failed', 'code.resend', verify_session_id=verify_session_id, event='verify.code.send', status=response.status.name)
        return jsonify({'success': False, 'error_message': response.error_message})

    if response.status == VerificationStatus.WAIT_CODE:
        _flow_log('info', 'Code resend successful', 'code.resend', verify_session_id=verify_session_id, event='verify.code.send', status=response.status.name)
        return jsonify({'success': True})

    _flow_log('error', 'Unexpected code_resend status', 'code.resend', verify_session_id=verify_session_id, event='verify.code.send')
    abort(500)


@hotspot_bp.route('/code/auth', methods=['POST'])
def code_auth():
    verify_session_id = session.get('verify_session_id')
    form_code = request.form.get('code')

    if form_code is None:
        session['error'] = get_translate('errors.auth.missing_code')
        _flow_log('warning', 'Missing code in code_auth request', 'code.auth', verify_session_id=verify_session_id, event='verify.code.check')
        return redirect(url_for('pages.hotspot.code_send'), 302)

    if not verify_session_id:
        _flow_log('warning', 'Missing verify_session_id in code_auth', 'code.auth', event='verify.code.check')
        abort(400)

    verify_service = Verification(
        verify_session_id,
        flow_ctx=_build_flow_ctx('code.auth', verify_session_id=verify_session_id, event='verify.code.check'),
    )
    verify_response = verify_service.code_verification(form_code)

    _flow_log(
        'debug',
        f'Code verification result: {verify_response.status.name}',
        'code.auth',
        verify_session_id=verify_session_id,
        event='verify.code.check',
        status=verify_response.status.name,
    )

    if verify_response.status == VerificationStatus.FAILED:
        session['error'] = verify_response.error_message
        return redirect(url_for('pages.hotspot.code_send'), 302)

    if verify_response.status == VerificationStatus.RETRY:
        session['error'] = verify_response.error_message
        _flow_log('warning', 'Invalid code, retry allowed', 'code.auth', verify_session_id=verify_session_id, event='verify.code.check', status='RETRY')
        return redirect(url_for('pages.hotspot.code_send'), 307)

    if verify_response.status == VerificationStatus.DENIED:
        session['error'] = verify_response.error_message
        session.pop('phone', None)
        session.pop('verify_session_id', None)
        _flow_log('warning', 'Code verification denied, resetting verification session', 'code.auth', verify_session_id=verify_session_id, event='verify.code.check', status='DENIED')
        return redirect(url_for('pages.hotspot.login'), 302)

    if verify_response.status == VerificationStatus.VERIFIED:
        session.pop('verify_session_id', None)
        mac = session.get('mac')
        phone = session.get('phone')
        hardware_fp = session.get('hardware_fp')

        auth_service = Authorization()
        auth_response = auth_service.authorization(
            mac,
            phone,
            hardware_fp,
            flow_ctx=_build_flow_ctx('code.auth', verify_session_id=verify_session_id, event='auth.finalize'),
        )
        _flow_log(
            'debug',
            f'Finalize auth result: {auth_response.status.name}',
            'code.auth',
            verify_session_id=verify_session_id,
            event='auth.finalize',
            status=auth_response.status.name,
        )
        if auth_response.status == AuthStatus.BLOCKED:
            _flow_log('warning', 'Finalize auth blocked', 'code.auth', verify_session_id=verify_session_id, event='auth.finalize', status='BLOCKED')
            abort(403)
        if auth_response.status == AuthStatus.AUTHORIZED:
            session['user_fp'] = auth_response.user_fp
            _flow_log('info', 'Flow finalized and authorized', 'code.auth', verify_session_id=verify_session_id, event='auth.flow.end', status='AUTHORIZED')
            return redirect(url_for('pages.hotspot.sendin'), 302)
        if auth_response.status == AuthStatus.FAILED:
            session['error'] = auth_response.error_message
            session.pop('phone', None)
            _flow_log('warning', 'Finalize auth failed', 'code.auth', verify_session_id=verify_session_id, event='auth.finalize', status='FAILED')
            return redirect(url_for('pages.hotspot.login'), 302)

    _flow_log('error', 'Unexpected code_auth status', 'code.auth', verify_session_id=verify_session_id, event='verify.code.check')
    abort(500)


@hotspot_bp.route('/call/check/poll', methods=['GET'])
def call_check_poll():
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        _flow_log('warning', 'Missing verify_session_id in call_check_poll', 'call.check', event='verify.call.poll')
        abort(400)

    payload = _get_call_verification_payload(verify_session_id)
    if payload.get('state') == 'verified':
        session.pop('verify_session_id', None)
    return jsonify(payload)


@hotspot_bp.route('/call/check/stream', methods=['GET'])
def call_check_stream():
    verify_session_id = session.get('verify_session_id')
    if not verify_session_id:
        _flow_log('warning', 'Missing verify_session_id in call_check_stream', 'call.check', event='verify.call.poll')
        abort(400)

    poll_interval_seconds = 2
    stream_ctx = _build_flow_ctx('call.check', verify_session_id=verify_session_id, event='verify.call.poll')

    def event_stream():
        yield "retry: 3000\n\n"

        while True:
            payload = _get_call_verification_payload(verify_session_id, base_ctx=stream_ctx)
            _flow_log(
                'debug',
                f'Call stream poll state: {payload.get("state")}',
                'call.check',
                verify_session_id=verify_session_id,
                base_ctx=stream_ctx,
                event='verify.call.poll',
                state=payload.get('state'),
            )

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
    hardware_fp = session.get('hardware_fp')
    verify_session_id = session.get('verify_session_id')
    if not mac or not phone or not hardware_fp:
        _flow_log('warning', 'Missing required session data in call_auth', 'call.auth', verify_session_id=verify_session_id, event='auth.finalize')
        abort(400)

    auth_service = Authorization()
    auth_response = auth_service.authorization(
        mac,
        phone,
        hardware_fp,
        flow_ctx=_build_flow_ctx('call.auth', verify_session_id=verify_session_id, event='auth.finalize'),
    )
    if auth_response.status == AuthStatus.BLOCKED:
        _flow_log('warning', 'Call auth blocked', 'call.auth', verify_session_id=verify_session_id, event='auth.finalize', status='BLOCKED')
        abort(403)
    if auth_response.status == AuthStatus.AUTHORIZED:
        session['user_fp'] = auth_response.user_fp
        _flow_log('info', 'Call auth successful', 'call.auth', verify_session_id=verify_session_id, event='auth.flow.end', status='AUTHORIZED')
        return redirect(url_for('pages.hotspot.sendin'), 302)
    if auth_response.status == AuthStatus.FAILED:
        session['error'] = auth_response.error_message
        session.pop('phone', None)
        session.pop('verify_session_id', None)
        _flow_log('warning', 'Call auth failed', 'call.auth', verify_session_id=verify_session_id, event='auth.finalize', status='FAILED')
        return redirect(url_for('pages.hotspot.login'), 302)

    _flow_log('error', 'Unexpected call_auth status', 'call.auth', verify_session_id=verify_session_id, event='auth.finalize')
    abort(500)


@hotspot_bp.route('/sendin', methods=['POST', 'GET'])
def sendin():
    phone_number = session.get('phone')
    verify_session_id = session.get('verify_session_id')
    if not phone_number:
        _flow_log('warning', 'Missing phone in sendin', 'sendin', verify_session_id=verify_session_id, event='auth.flow.end')
        abort(400)

    link_login_only = session.get('link-login-only')
    link_orig = session.get('link-orig')
    chap_id = session.get('chap-id')
    chap_challenge = session.get('chap-challenge')
    mac = session.get('mac')
    user_fp = session.get('user_fp')

    auth_service = Authorization()

    if not auth_service.authorized(user_fp):
        _flow_log('warning', 'Sendin authorization check failed', 'sendin', verify_session_id=verify_session_id, event='auth.flow.end', status='UNAUTHORIZED')
        session.clear()
        if link_login_only:
            session['link-login-only'] = link_login_only
        abort(401)

    _flow_log('info', 'Flow finished successfully, issuing credentials', 'sendin', verify_session_id=verify_session_id, event='auth.flow.end', status='AUTHORIZED')
    session.clear()

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
        link_orig=link_orig,
    )
