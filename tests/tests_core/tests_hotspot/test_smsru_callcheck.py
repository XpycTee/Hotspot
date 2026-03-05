import unittest
from unittest.mock import MagicMock, patch

from core.hotspot.verification.api import ConfirmStatus
from core.hotspot.verification.api.smsru import SMSRU


class TestSMSRUCallcheck(unittest.TestCase):
    @patch('core.hotspot.verification.api.smsru.Client')
    def test_check_polling_returns_pending_on_provider_connect_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.callcheck_status.side_effect = ConnectionRefusedError('connection refused')
        mock_client_cls.return_value = mock_client

        provider = SMSRU('test-api-key')
        result = provider.check_polling('check-id')

        self.assertEqual(result.status, ConfirmStatus.PENDING)

