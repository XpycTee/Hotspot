import unittest

from core.admin.auth.login import handle_failed_login, login_by_password
from core.cache import get_cache
from core.config.admin import ADMIN
from core.utils.language import get_translate


class TestCoreAdmin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        cache = get_cache()
        cache.clear()

    def test_handle_failed_login(self):
        session_id = 'test_handle_failed_login'
        lockout_time = ADMIN.get('lockout_time')
        max_login_attempts = ADMIN.get('max_login_attempts')
        before_lockout = get_translate('errors.admin.wrong_credentials')
        after_lockout = get_translate('errors.admin.end_tries', templates={'lockout_time': lockout_time})

        expected_responses = [before_lockout] * (max_login_attempts - 1) + [after_lockout]

        for expected in expected_responses:
            error_message = handle_failed_login(session_id)
            self.assertEqual(error_message, expected)

    def test_login_by_password(self):
        lockout_time = ADMIN.get('lockout_time')
        max_login_attempts = ADMIN.get('max_login_attempts')
        expected_responses = [
            {'status': 'OK'},
            {'status': 'BAD_LOGIN', 'error_message': get_translate('errors.admin.wrong_credentials')},
            {'status': 'BAD_LOGIN', 'error_message': get_translate('errors.admin.end_tries', templates={'lockout_time': lockout_time})},
            {'status': 'LOCKOUT', 'error_message': get_translate('errors.admin.end_tries', templates={'lockout_time': lockout_time})}
        ]

        response = login_by_password('Good_Session', 'admin', 'admin')
        self.assertEqual(response, expected_responses[0])

        for _ in range(max_login_attempts-1):
            response = login_by_password('Bad_Session', 'admin', 'wrong_passw')
            self.assertEqual(response, expected_responses[1])
        
        response = login_by_password('Bad_Session', 'admin', 'wrong_passw')
        self.assertEqual(response, expected_responses[2])

        response = login_by_password('Bad_Session', 'admin', 'wrong_passw')
        self.assertEqual(response, expected_responses[3])