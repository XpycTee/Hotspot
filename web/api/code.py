from flask import Blueprint, abort, jsonify, session


from core.hotspot.verification.code import send_code
import web.logger as logger

code_bp = Blueprint('code', __name__, url_prefix='/code')


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


@code_bp.route('/resend', methods=['POST'])
def resend():
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
