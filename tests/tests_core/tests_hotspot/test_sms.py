import unittest
from unittest.mock import patch

from core.hotspot.sms.code import clear_code, code_sended, generate_code, get_code, increment_attempts, send_code, set_sended, verify_code


class TestCoreHotpsotSMSCode(unittest.TestCase):
    @patch('core.hotspot.sms.code.get_cache')
    def test_generate_code(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value
        mock_cache.set = unittest.mock.MagicMock()

        code = generate_code('abc123')

        self.assertEqual(len(code), 4)
        mock_cache.set.assert_any_call('sms:code:abc123', code, timeout=300)
        mock_cache.set.assert_any_call('sms:attempts:abc123', 0, timeout=300)
        mock_cache.set.assert_any_call('sms:sended:abc123', False, timeout=60)

    @patch('core.hotspot.sms.code.get_cache')
    def test_get_code(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.return_value = '1234'

        result = get_code('sid1')
        self.assertEqual(result, '1234')
        mock_cache.get.assert_called_once_with('sms:code:sid1')

    @patch('core.hotspot.sms.code.get_cache')
    def test_set_sended(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value

        set_sended('sid2')
        mock_cache.set.assert_called_once_with('sms:sended:sid2', True, timeout=60)

    @patch('core.hotspot.sms.code.get_cache')
    def test_increment_attempts(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.return_value = 1

        result = increment_attempts('sid3')

        mock_cache.inc.assert_called_once_with('sms:attempts:sid3')
        self.assertEqual(result, 1)

    @patch('core.hotspot.sms.code.get_cache')
    def test_verify_code(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.return_value = '1111'

        self.assertTrue(verify_code('s1', '1111'))
        self.assertFalse(verify_code('s1', '2222'))

    @patch('core.hotspot.sms.code.get_cache')
    def test_code_sended(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.return_value = True

        self.assertTrue(code_sended('s2'))
        mock_cache.get.assert_called_once_with('sms:sended:s2')

    @patch('core.hotspot.sms.code.get_cache')
    def test_clear_code(self, mock_get_cache):
        mock_cache = mock_get_cache.return_value

        clear_code('s3')

        mock_cache.delete.assert_any_call('sms:code:s3')
        mock_cache.delete.assert_any_call('sms:attempts:s3')
        mock_cache.delete.assert_any_call('sms:sended:s3')

    @patch('core.hotspot.sms.code.get_sender')
    @patch('core.hotspot.sms.code.get_cache')
    def test_send_code_already_sended(self, mock_get_cache, mock_get_sender):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.return_value = True  # code_sended = True

        result = send_code('sid', '79990000000')
        self.assertEqual(result['status'], 'ALREDY_SENDED')

    @patch('core.hotspot.sms.code.get_sender')
    @patch('core.hotspot.sms.code.get_cache')
    @patch('core.hotspot.sms.code.get_translate', return_value='SMS: 1234')
    def test_send_code_sends_correctly(self, mock_translate, mock_get_cache, mock_get_sender):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.side_effect = [False, None]  # not sent, no cached code

        mock_sender = mock_get_sender.return_value
        mock_sender.send_sms.return_value = None  # no error

        result = send_code('sid55', '79990000000')

        self.assertEqual(result['status'], 'OK')
        mock_sender.send_sms.assert_called_once()

    @patch('core.hotspot.sms.code.get_sender')
    @patch('core.hotspot.sms.code.get_cache')
    @patch('core.hotspot.sms.code.get_translate', return_value='SMS: 1234')
    def test_send_code_sender_error(self, mock_translate, mock_get_cache, mock_get_sender):
        mock_cache = mock_get_cache.return_value
        mock_cache.get.side_effect = [False, None]

        mock_sender = mock_get_sender.return_value
        mock_sender.send_sms.return_value = 'ERROR'

        result = send_code('sid66', '79990000000')

        self.assertEqual(result['status'], 'SENDER_ERROR')