import datetime
import unittest
from unittest.mock import MagicMock, patch

from core.config import init_config
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
