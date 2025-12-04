import datetime
import unittest

from core import database
from core.admin.auth.attempts import increment_attempts, reset_attempts
from core.admin.auth.lockout import check_lockout, update_lockout
from core.admin.auth.login import handle_failed_login, login_by_password
from core.admin.auth.security import check_password
from core.admin.tables import get_table
from core.admin.tables.blacklist import get_blacklist
from core.admin.tables.employee import get_employees
from core.admin.tables.wifi_clients import get_wifi_clients
from core.cache import get_cache
from core.config.admin import ADMIN
from core.utils.language import get_translate


class TestCoreAdminAuth(unittest.TestCase):
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

    def test_check_password(self):
        expected_data = [
            (('admin', 'admin'), True),
            (('sombody', 'qwerty'), False),
        ]
        for expected_creds, expected in expected_data:
            result = check_password(*expected_creds)
            
            self.assertIs(result, expected)

    def test_check_lockout(self):
        result = check_lockout('None')
        self.assertIsNone(result)

        cache = get_cache()
        yesterday = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp()
        cache.set(f'admin:login:lockout:Good', yesterday)

        result = check_lockout('Good')
        self.assertTrue(result)

        start_epoche = datetime.datetime(1970, 1, 1).timestamp()
        cache.set(f'admin:login:lockout:Expired', start_epoche)

        result = check_lockout('Expired')
        self.assertFalse(result)

    def test_update_lockout(self):
        update_lockout('Updated')

        result = check_lockout('Updated')
        self.assertTrue(result)

    def test_increment_attempts(self):
        result = increment_attempts('Null')
        self.assertEqual(result, 1)

        cache = get_cache()
        cache.set('admin:login:attempts:Big', 10)
        result = increment_attempts('Big')
        self.assertEqual(result, 11)

    def test_reset_attempts(self):
        cache = get_cache()
        cache.set('admin:login:attempts:Reset', 10)
        cache.set('admin:login:lockout:Reset', True)

        reset_attempts('Reset')
        
        result = cache.get('admin:login:attempts:Reset')
        self.assertIsNone(result)
        result = cache.get('admin:login:lockout:Reset')
        self.assertIsNone(result)


class TestCoreAdminTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()

    def test_get_wifi_clients(self):
        expected = {'wifi_clients': [], 'total_rows': 0}
        result = get_wifi_clients(1, 10)
        self.assertEqual(result, expected)
            
    def test_get_employees(self):
        expected = {'employees': [], 'total_rows': 0}
        result = get_employees(1, 10)
        self.assertEqual(result, expected)

    def test_get_blacklist(self):
        expected = {'blacklist': [], 'total_rows': 0}
        result = get_blacklist(1, 10)
        self.assertEqual(result, expected)