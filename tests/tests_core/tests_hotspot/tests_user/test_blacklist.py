import datetime
import unittest
from unittest.mock import patch

from core import database
from core.database.models import Model
from core.database.models.blacklist import Blacklist
from core.database.models.clients_number import ClientsNumber
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.user.blacklist import add_to_blacklist, add_to_blacklist_by_mac, check_blacklist, delete_from_blacklist


class TestCoreHotpsotUserBlacklist(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()

    def tearDown(self):
        self._clear_users()
    
    @staticmethod
    def _clear_users():
        with get_session() as db_session:
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()


    @staticmethod
    def _db_non_blocked(mac=None, phone_number=None):
        if not mac:
            mac = '00:00:00:00:00:01'

        if not phone_number:
            phone_number = '70000000001'

        with get_session() as db_session:
            blocked_client = ClientsNumber(
                phone_number=phone_number, 
                last_seen=datetime.datetime.now()
            )
            db_session.add(blocked_client)
            db_session.commit()
            blocked_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime.now() + datetime.timedelta(days=1), 
                employee=False, 
                phone=blocked_client, 
                user_fp=None
            )
            db_session.add(blocked_wifi_client)

    @staticmethod
    def _db_blocked(phone_number=None):
        if not phone_number:
            phone_number = '70000000002'

        with get_session() as db_session:
            new_blocked_phone = Blacklist(phone_number=phone_number)
            db_session.add(new_blocked_phone)
            db_session.commit()

    @patch('core.hotspot.user.blacklist.get_translate', return_value='ERROR_TEXT')
    def test_add_to_blacklist(self, *args):
        expected = {'status': 'OK'}
        result = add_to_blacklist('70000000000')
        self.assertDictEqual(result, expected)

        expected = {'status': 'ALREDY_BLOCKED', 'error_message': 'ERROR_TEXT'}
        result = add_to_blacklist('70000000000')
        self.assertDictEqual(result, expected)


    def test_delete_from_blacklist(self):
        self._db_blocked('70000000002')
        expected = {'status': 'OK'}
        result = delete_from_blacklist('70000000002')
        self.assertDictEqual(result, expected)

    @patch('core.hotspot.user.blacklist.get_translate', return_value='ERROR_TEXT')
    def test_add_to_blacklist_by_mac(self, *args):
        self._db_non_blocked('00:00:00:00:00:01', '70000000001')
        expected = {'status': 'OK'}
        result = add_to_blacklist_by_mac('00:00:00:00:00:01')
        self.assertDictEqual(result, expected)

        expected = {'status': 'ALREDY_BLOCKED', 'error_message': 'ERROR_TEXT'}
        result = add_to_blacklist_by_mac('00:00:00:00:00:01')
        self.assertDictEqual(result, expected)

        expected = {'status': 'NOT_FOUND', 'error_message': 'ERROR_TEXT'}
        result = add_to_blacklist_by_mac('FF:FF:FF:FF:FF:01')
        self.assertDictEqual(result, expected)

    def test_check_blacklist(self):
        self._db_blocked('70000000002')

        result = check_blacklist('70000000002')
        self.assertTrue(result)

        result = check_blacklist('70000000000')
        self.assertFalse(result)
