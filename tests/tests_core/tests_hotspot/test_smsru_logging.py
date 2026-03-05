import unittest
from unittest.mock import MagicMock, patch

from core.hotspot.verification.api import ConfirmStatus, DeliveryStatus
from core.hotspot.verification.api.smsru import SMSRU


class TestSMSRULogging(unittest.TestCase):
    @patch('core.hotspot.verification.api.smsru.get_translate', return_value='code message')
    @patch('core.hotspot.verification.api.smsru.logger.error')
    def test_send_code_error_logs_whitelisted_fields_only(self, mock_logger_error, _):
        provider = SMSRU('api-key')
        provider._api = MagicMock()
        provider._api.send.return_value = {
            'status': 'ERROR',
            'status_code': 500,
            'status_text': 'upstream failed',
            'raw_payload': 'SHOULD_NOT_BE_LOGGED',
        }

        result = provider.send_code('79990000000', '1234')

        self.assertEqual(result.status, DeliveryStatus.ERROR)
        message, = mock_logger_error.call_args[0]
        self.assertNotIn('SHOULD_NOT_BE_LOGGED', message)

        extra = mock_logger_error.call_args[1].get('extra', {})
        self.assertEqual(extra.get('status'), 'ERROR')
        self.assertEqual(extra.get('status_code'), 500)
        self.assertEqual(extra.get('error_kind'), 'provider_error')

    @patch('core.hotspot.verification.api.smsru.logger.error')
    def test_check_polling_invalid_response_logs_without_raw_payload(self, mock_logger_error):
        provider = SMSRU('api-key')
        provider._api = MagicMock()
        provider._api.callcheck_status.return_value = {
            'status': 'OK',
            'check_status': 'not-int',
            'raw_payload': 'SHOULD_NOT_BE_LOGGED',
        }

        result = provider.check_polling('req-1')

        self.assertEqual(result.status, ConfirmStatus.ERROR)
        message, = mock_logger_error.call_args[0]
        self.assertNotIn('SHOULD_NOT_BE_LOGGED', message)

        extra = mock_logger_error.call_args[1].get('extra', {})
        self.assertEqual(extra.get('error_kind'), 'invalid_response')
        self.assertEqual(extra.get('request_id'), 'req-1')
