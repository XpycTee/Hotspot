import unittest
from unittest.mock import MagicMock, patch

from core.hotspot.verification.api import ConfirmStatus
from core.hotspot.verification.api.asterisk import AsteriskConfirm


class TestAsteriskCallcheckLogging(unittest.TestCase):
    @patch('core.hotspot.verification.api.asterisk.logger')
    @patch('core.hotspot.verification.api.asterisk.get_cache')
    def test_check_verification_pending_does_not_log_error(self, mock_get_cache, mock_logger):
        fake_cache = MagicMock()
        fake_cache.get.return_value = {'status': False, 'phone': '79990000000'}
        mock_get_cache.return_value.__enter__.return_value = fake_cache

        provider = AsteriskConfirm(call_phone='70000000000')
        result = provider.check_verification('req-1')

        self.assertEqual(result.status, ConfirmStatus.PENDING)
        mock_logger.error.assert_not_called()
        mock_logger.debug.assert_called_once()

