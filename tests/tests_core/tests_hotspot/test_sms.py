import datetime
import unittest
from unittest.mock import MagicMock, patch

from core.config import init_config
from core.config.models.verificators import VProviderType, VerificationMethod
from core.hotspot.verification.router import VRouterStatus, VRouterResponse
from core.hotspot.verification.service import Verification, VerificationStatus, VSessionStatus


class TestCoreHotspotVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_config('web')

    def test_code_verification_retry_and_denied(self):
        service = Verification('verify-retry')
        service._session.status = VSessionStatus.WAIT_CODE
        service._session.code = '1111'
        service._session.attempts = 0
        service._session.timeout = datetime.datetime.now() + datetime.timedelta(minutes=5)
        service._save_session()

        self.assertEqual(service.code_verification('0000').status, VerificationStatus.RETRY)
        self.assertEqual(service.code_verification('0000').status, VerificationStatus.RETRY)
        self.assertEqual(service.code_verification('0000').status, VerificationStatus.DENIED)

    def test_code_verification_verified(self):
        service = Verification('verify-ok')
        service._session.status = VSessionStatus.WAIT_CODE
        service._session.code = '1234'
        service._session.attempts = 0
        service._session.timeout = datetime.datetime.now() + datetime.timedelta(minutes=5)
        service._save_session()

        result = service.code_verification('1234')
        self.assertEqual(result.status, VerificationStatus.VERIFIED)

    def test_code_verification_expired(self):
        service = Verification('verify-expired')
        service._session.status = VSessionStatus.WAIT_CODE
        service._session.code = '1234'
        service._session.timeout = datetime.datetime.now() - datetime.timedelta(seconds=1)
        service._save_session()

        result = service.code_verification('1234')
        self.assertEqual(result.status, VerificationStatus.FAILED)

    @patch('core.hotspot.verification.service.VerificationRouter')
    def test_send_code_wait_code(self, mock_router_cls):
        mock_router = MagicMock()
        mock_router.send_code.return_value = VRouterResponse(status=VRouterStatus.SENDED)
        mock_router_cls.return_value = mock_router

        service = Verification('send-code')
        service._session.phone = '79990000000'
        service._session.status = VSessionStatus.START

        result = service.send_code()
        self.assertEqual(result.status, VerificationStatus.WAIT_CODE)

    @patch('core.hotspot.verification.service.logger.debug')
    @patch('core.hotspot.verification.service.VerificationRouter')
    def test_send_code_does_not_log_otp_value(self, mock_router_cls, mock_logger_debug):
        mock_router = MagicMock()
        mock_router.send_code.return_value = VRouterResponse(status=VRouterStatus.SENDED)
        mock_router_cls.return_value = mock_router

        service = Verification('send-code-safe')
        service._session.phone = '79990000000'
        service._session.status = VSessionStatus.START
        service._session.code = '4321'
        service._save_session()

        result = service.send_code()
        self.assertEqual(result.status, VerificationStatus.WAIT_CODE)

        debug_messages = [args[0] for args, _ in mock_logger_debug.call_args_list]
        self.assertTrue(all('4321' not in msg for msg in debug_messages))

    @patch('core.hotspot.verification.service.logger.warning')
    @patch('core.hotspot.verification.service.logger.info')
    def test_code_verification_logs_state_transitions(self, mock_logger_info, mock_logger_warning):
        service = Verification('verify-logs')
        service._session.status = VSessionStatus.WAIT_CODE
        service._session.code = '1111'
        service._session.attempts = 0
        service._session.timeout = datetime.datetime.now() + datetime.timedelta(minutes=5)
        service._save_session()

        self.assertEqual(service.code_verification('0000').status, VerificationStatus.RETRY)
        self.assertEqual(service.code_verification('0000').status, VerificationStatus.RETRY)
        self.assertEqual(service.code_verification('1111').status, VerificationStatus.VERIFIED)

        warning_messages = [args[0] for args, _ in mock_logger_warning.call_args_list]
        info_messages = [args[0] for args, _ in mock_logger_info.call_args_list]
        self.assertTrue(any('Code verification retry required' in msg for msg in warning_messages))
        self.assertTrue(any('Code verification passed' in msg for msg in info_messages))

    @patch('core.hotspot.verification.service.VerificationRouter')
    def test_start_verification_saves_hotspot_context_and_request_mapping(self, mock_router_cls):
        mock_router = MagicMock()
        mock_router.available_methods = {VerificationMethod.CALL}
        mock_router.start_confirm.return_value = VRouterResponse(
            status=VRouterStatus.SENDED,
            provider=VProviderType.SMSRU,
            request_id='request-1',
            call_phone='79990001122',
        )
        mock_router_cls.return_value = mock_router

        service = Verification('verify-request-map')
        service.set_hotspot_context('AA:BB:CC:00:00:01', 'fp-hw')
        service.mark_trial_issued()
        result = service.start_verification('79990000000')

        self.assertEqual(result.status, VerificationStatus.WAIT_CALL)
        self.assertEqual(service.session.mac, 'AA:BB:CC:00:00:01')
        self.assertEqual(service.session.hardware_fp, 'fp-hw')
        self.assertTrue(service.session.trial_issued)
        self.assertEqual(
            Verification.resolve_session_id_by_request('smsru', 'request-1'),
            'verify-request-map',
        )
