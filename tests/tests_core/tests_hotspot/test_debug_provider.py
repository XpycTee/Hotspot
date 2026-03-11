import unittest
from unittest.mock import patch

from core.hotspot.verification.api import DeliveryStatus
from core.hotspot.verification.api.debug import DebugCodeDelivery


class TestDebugCodeDelivery(unittest.TestCase):
    @patch('builtins.print')
    def test_send_code_prints_otp_to_terminal(self, mock_print):
        provider = DebugCodeDelivery()

        result = provider.send_code('79990000000', '1234')

        self.assertEqual(result.status, DeliveryStatus.SENT)
        mock_print.assert_called_once_with(
            '[Debug Code Delivery Provider] verification code for 79990000000: 1234',
            flush=True,
        )

