import unittest
from unittest.mock import patch

from core.config import init_config
from core.hotspot.authorization.service import AuthResponse, AuthStatus
from core.hotspot.verification.service import Verification
from core.hotspot.verification.webhook_finalize import finalize_verified_trial
from core.hotspot.wifi.coa import CoAResult
from core.redis import get_cache


class TestWebhookFinalize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_config('web')

    def tearDown(self):
        with get_cache() as cache:
            cache.clear()

    def _prepare_verification(self, verify_session_id='verify-1'):
        service = Verification(verify_session_id)
        service.set_hotspot_context('AA:BB:CC:00:00:11', 'fp-hw')
        service._session.phone = '79990000000'
        service.mark_trial_issued()
        service._save_session()
        with get_cache() as cache:
            cache.set('verify:request:smsru:req-1', verify_session_id, 600)
            cache.set('auth:trial:nas:aa:bb:cc:00:00:11', {'nas_ip': '10.0.0.1', 'radius_client_ip': '10.0.0.2'}, 300)

    @patch('core.hotspot.verification.webhook_finalize.delete_trial_token')
    @patch('core.hotspot.verification.webhook_finalize.send_group_switch')
    @patch('core.hotspot.verification.webhook_finalize.find_by_mac')
    @patch('core.hotspot.verification.webhook_finalize.Authorization.authorization')
    def test_finalize_trial_runs_db_finalize_even_if_coa_fail(
        self,
        mock_authorization,
        mock_find_by_mac,
        mock_send_group_switch,
        mock_delete_trial_token,
    ):
        self._prepare_verification()
        mock_authorization.return_value = AuthResponse(status=AuthStatus.AUTHORIZED)
        mock_find_by_mac.return_value = {'is_employee': False}
        mock_send_group_switch.return_value = CoAResult(success=False, error_message='timeout')

        result = finalize_verified_trial('smsru', 'req-1')

        self.assertEqual(result.status, 'OK')
        mock_authorization.assert_called_once()
        mock_send_group_switch.assert_called_once()
        mock_delete_trial_token.assert_called_once_with('AA:BB:CC:00:00:11')

        service = Verification('verify-1')
        self.assertTrue(service.session.webhook_finalized)
        with get_cache() as cache:
            self.assertIsNone(cache.get('verify:request:smsru:req-1'))
            self.assertIsNone(cache.get('auth:trial:nas:aa:bb:cc:00:00:11'))

    @patch('core.hotspot.verification.webhook_finalize.Authorization.authorization')
    def test_finalize_trial_is_idempotent(self, mock_authorization):
        self._prepare_verification()
        service = Verification('verify-1')
        service.mark_webhook_finalized()

        result = finalize_verified_trial('smsru', 'req-1')

        self.assertEqual(result.status, 'ALREADY_FINALIZED')
        mock_authorization.assert_not_called()
