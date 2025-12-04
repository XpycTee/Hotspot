import datetime
import unittest
from unittest.mock import patch

from sqlalchemy import select

from core import database
from core.database.models import Model
from core.database.models.clients_number import ClientsNumber
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.user.expiration import get_delay, new_expiration, reset_expiration, update_expiration


class TestCoreHotpsotUserExpiration(unittest.TestCase):
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
    def _create_wifi_client(mac=None, phone_number=None, is_employee=False):
        if not mac:
            mac = 'BB:BB:BB:00:00:01'
        if not phone_number:
            phone_number = '79990000010'

        with get_session() as db_session:
            client = ClientsNumber(
                phone_number=phone_number,
                last_seen=datetime.datetime.now()
            )
            db_session.add(client)
            db_session.commit()

            wifi_client = WifiClient(
                mac=mac,
                employee=is_employee,
                phone=client,
                expiration=datetime.datetime.now() + datetime.timedelta(days=1)
            )
            db_session.add(wifi_client)
            db_session.commit()

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(days=30)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(days=1)})
    def test_get_delay_employee(self, *args):
        result = get_delay(is_employee=True)
        self.assertEqual(result, datetime.timedelta(days=30))

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(days=30)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(days=1)})
    def test_get_delay_guest(self, *args):
        result = get_delay(is_employee=False)
        self.assertEqual(result, datetime.timedelta(days=1))

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(hours=8)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(hours=2)})
    def test_new_expiration_employee_before_6am(self, *args):
        with patch('core.hotspot.user.expiration.datetime') as mock_datetime:
            today = datetime.date.today()
            current_time = datetime.datetime.combine(today, datetime.time(3, 0))
            mock_datetime.datetime.now.return_value = current_time
            mock_datetime.datetime.combine = datetime.datetime.combine
            mock_datetime.date.today = datetime.date.today
            mock_datetime.time = datetime.time
            mock_datetime.timedelta = datetime.timedelta

            result = new_expiration(is_employee=True)

            expected_start = datetime.datetime.combine(today, datetime.time(6, 0))
            expected = expected_start + datetime.timedelta(hours=8)
            self.assertEqual(result, expected)

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(hours=8)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(hours=2)})
    def test_new_expiration_employee_after_6am(self, *args):
        with patch('core.hotspot.user.expiration.datetime') as mock_datetime:
            today = datetime.date.today()
            current_time = datetime.datetime.combine(today, datetime.time(15, 0))
            mock_datetime.datetime.now.return_value = current_time
            mock_datetime.datetime.combine = datetime.datetime.combine
            mock_datetime.date.today = datetime.date.today
            mock_datetime.time = datetime.time
            mock_datetime.timedelta = datetime.timedelta

            result = new_expiration(is_employee=True)

            expected_start = datetime.datetime.combine(today, datetime.time(6, 0))
            expected = expected_start + datetime.timedelta(hours=8) + datetime.timedelta(days=1)
            self.assertEqual(result, expected)

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(hours=8)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(hours=2)})
    def test_new_expiration_guest(self, *args):
        with patch('core.hotspot.user.expiration.datetime') as mock_datetime:
            today = datetime.date.today()
            current_time = datetime.datetime.combine(today, datetime.time(10, 0))
            mock_datetime.datetime.now.return_value = current_time
            mock_datetime.datetime.combine = datetime.datetime.combine
            mock_datetime.date.today = datetime.date.today
            mock_datetime.time = datetime.time
            mock_datetime.timedelta = datetime.timedelta

            result = new_expiration(is_employee=False)

            expected_start = datetime.datetime.combine(today, datetime.time(6, 0))
            expected = expected_start + datetime.timedelta(hours=2) + datetime.timedelta(days=1)
            self.assertEqual(result, expected)

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(days=30)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(days=1)})
    def test_update_expiration_employee(self, *args):
        mac = 'CC:CC:CC:00:00:01'
        self._create_wifi_client(mac=mac, is_employee=True)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            old_expiration = wifi_client.expiration
            self.assertIsNotNone(old_expiration)

        update_expiration(mac)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            new_expiration_time = wifi_client.expiration
            self.assertNotEqual(new_expiration_time, old_expiration)
            self.assertGreater(new_expiration_time, datetime.datetime.now())

    @patch('core.hotspot.user.expiration.STAFF_USER', {'delay': datetime.timedelta(days=30)})
    @patch('core.hotspot.user.expiration.GUEST_USER', {'delay': datetime.timedelta(days=1)})
    def test_update_expiration_guest(self, *args):
        mac = 'DD:DD:DD:00:00:01'
        self._create_wifi_client(mac=mac, is_employee=False)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            old_expiration = wifi_client.expiration
            self.assertIsNotNone(old_expiration)

        update_expiration(mac)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            new_expiration_time = wifi_client.expiration
            self.assertNotEqual(new_expiration_time, old_expiration)
            self.assertGreater(new_expiration_time, datetime.datetime.now())

    def test_reset_expiration(self):
        mac = 'EE:EE:EE:00:00:01'
        self._create_wifi_client(mac=mac, is_employee=True)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            self.assertGreater(wifi_client.expiration, datetime.datetime(1970, 1, 1))

        reset_expiration(mac)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            self.assertEqual(wifi_client.expiration, datetime.datetime(1970, 1, 1))

    def test_reset_expiration_guest(self):
        mac = 'FF:FF:FF:00:00:01'
        self._create_wifi_client(mac=mac, is_employee=False)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            self.assertGreater(wifi_client.expiration, datetime.datetime(1970, 1, 1))

        reset_expiration(mac)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac == mac)
            wifi_client = db_session.scalars(query).first()
            self.assertEqual(wifi_client.expiration, datetime.datetime(1970, 1, 1))
