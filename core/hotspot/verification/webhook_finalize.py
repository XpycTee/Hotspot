from dataclasses import dataclass
from typing import Any

from core.hotspot.authorization.service import AuthStatus, Authorization
from core.hotspot.user.token import delete_trial_token
from core.hotspot.verification.service import Verification
from core.hotspot.wifi.coa import send_group_switch
from core.hotspot.wifi.repository import find_by_mac
from core.logging import get_logger
from core.redis import get_cache


logger = get_logger('core.hotspot.verification.webhook_finalize')


@dataclass
class FinalizeResult:
    status: str
    message: str | None = None


def _normalize_mac(mac: str | None) -> str | None:
    if not mac:
        return None
    return mac.strip().replace('-', ':').lower()


def _trial_nas_cache_key(mac: str) -> str:
    return f'auth:trial:nas:{_normalize_mac(mac)}'


def _verify_request_key(provider: str, request_id: str) -> str:
    return f'verify:request:{provider}:{request_id}'


def _resolve_target_group(mac: str) -> str:
    wifi_client = find_by_mac(mac)
    if wifi_client and wifi_client.get('is_employee'):
        return 'employee'
    return 'guest'


def finalize_verified_trial(provider: str, request_id: str) -> FinalizeResult:
    verify_session_id = Verification.resolve_session_id_by_request(provider, request_id)
    if not verify_session_id:
        return FinalizeResult(status='NOT_FOUND')

    service = Verification(verify_session_id, flow_ctx={'stage': 'webhook.finalize'})
    session = service.session
    if session.webhook_finalized:
        return FinalizeResult(status='ALREADY_FINALIZED')
    if not session.trial_issued:
        return FinalizeResult(status='TRIAL_NOT_ISSUED')
    if not session.mac or not session.phone or not session.hardware_fp:
        return FinalizeResult(status='MISSING_CONTEXT')

    auth_service = Authorization()
    auth_response = auth_service.authorization(
        session.mac,
        session.phone,
        session.hardware_fp,
        flow_ctx={'stage': 'webhook.finalize', 'verify_session_id': verify_session_id, 'event': 'auth.finalize'},
    )
    if auth_response.status != AuthStatus.AUTHORIZED:
        return FinalizeResult(status='AUTH_NOT_AUTHORIZED')

    nas_target: dict[str, Any] | None = None
    with get_cache() as cache:
        nas_target = cache.get(_trial_nas_cache_key(session.mac))

    target_group = _resolve_target_group(session.mac)
    coa_result = send_group_switch(session.mac, target_group, nas_target)

    service.mark_webhook_finalized()
    with get_cache() as cache:
        cache.delete(_verify_request_key(provider, request_id))
        cache.delete(_trial_nas_cache_key(session.mac))
    delete_trial_token(session.mac)

    if coa_result.success and coa_result.operation == 'disconnect_fallback':
        logger.info(
            'Webhook trial finalization completed via disconnect fallback',
            extra={
                'event': 'verify.webhook.finalize',
                'provider': provider,
                'verify_session_id': verify_session_id,
                'target_group': target_group,
            },
        )
    elif coa_result.success:
        logger.info(
            'Webhook trial finalization completed with CoA ACK',
            extra={'event': 'verify.webhook.finalize', 'provider': provider, 'verify_session_id': verify_session_id, 'target_group': target_group},
        )
    else:
        logger.warning(
            f'Webhook trial finalization completed with CoA failure: {coa_result.error_message}',
            extra={
                'event': 'verify.webhook.finalize',
                'provider': provider,
                'verify_session_id': verify_session_id,
                'target_group': target_group,
                'coa_error': coa_result.error_message,
            },
        )
    return FinalizeResult(status='OK')
