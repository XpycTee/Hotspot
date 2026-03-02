import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from core import database
from core.config import init_config
from core.database.models import Model
from core.database.models.clients_number import ClientsNumber
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.wifi.auth import get_credentials
from core.hotspot.wifi.challange import _octal_string_to_bytes, hash_chap
from core.hotspot.wifi.fingerprint import hash_fingerprint, update_fingerprint
from core.hotspot.wifi.repository import create_or_udpate_wifi_client, find_by_fp, find_by_mac


def _clear_db():
    with get_session() as db_session:
        for table in reversed(Model.metadata.sorted_tables):
            if table.name == 'system_config':
                continue
            db_session.execute(table.delete())
        db_session.commit()


class TestCoreHotspotWiFi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_config('web')
        database.create_all()

    def setUp(self):
        _clear_db()

    def test_octal_string_to_bytes(self):
        self.assertEqual(_octal_string_to_bytes('\\141\\142\\143'), b'abc')

    def test_hash_chap(self):
        result = hash_chap('\\000', 'secret', '\\141\\142\\143')
        self.assertEqual(result, 'fddec1a3b42bee03237261fa3ad2f8bb')

    def test_hash_fingerprint(self):
        result = hash_fingerprint('79999999999', '0123456789abcdef')
        self.assertEqual(result, 'e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002')

    def test_update_fingerprint(self):
        with get_session() as db_session:
            db_session.add(WifiClient(mac='00:00:00:00:00:01', user_fp='old'))
            db_session.commit()

        update_fingerprint('00:00:00:00:00:01', 'new')

        with get_session() as db_session:
            result = db_session.scalars(select(WifiClient).where(WifiClient.mac == '00:00:00:00:00:01')).first()
            self.assertEqual(result.user_fp, 'new')

    def test_find_by_mac_and_fp(self):
        with get_session() as db_session:
            db_session.add(WifiClient(mac='00:00:00:00:00:01', user_fp='qwerty'))
            db_session.commit()

        by_mac = find_by_mac('00:00:00:00:00:01')
        by_fp = find_by_fp('qwerty')

        self.assertEqual(by_mac['mac'], '00:00:00:00:00:01')
        self.assertEqual(by_fp['mac'], '00:00:00:00:00:01')

    def test_create_or_update_wifi_client(self):
        mac = 'FF:FF:FF:00:00:01'
        phone_guest = '79999990001'
        phone_employee = '79999990002'

        create_or_udpate_wifi_client(mac, phone_guest)
        self.assertEqual(find_by_mac(mac)['is_employee'], False)

        with get_session() as db_session:
            employee = Employee(lastname='lastname', name='name')
            db_session.add(employee)
            db_session.flush()
            db_session.add(EmployeePhone(phone_number=phone_employee, employee=employee))
            db_session.commit()

        create_or_udpate_wifi_client(mac, phone_employee)
        self.assertEqual(find_by_mac(mac)['is_employee'], True)
        self.assertEqual(find_by_mac(mac)['phone'], phone_employee)

    @patch('core.hotspot.wifi.auth.generate_token')
    @patch('core.hotspot.wifi.auth.get_config')
    def test_get_credentials(self, mock_get_config, mock_generate_token):
        mock_config = MagicMock()
        mock_config.hotspot.staff.password = 'staff-secret'
        mock_config.hotspot.guest.password = 'guest-secret'
        mock_get_config.return_value = mock_config

        mock_config.radius.enabled = False
        with get_session() as db_session:
            employee = Employee(lastname='Emp', name='Loyee')
            db_session.add(employee)
            db_session.flush()
            db_session.add(EmployeePhone(phone_number='79990000001', employee=employee))
            employee_phone = ClientsNumber(phone_number='79990000001')
            guest_phone = ClientsNumber(phone_number='79990000002')
            db_session.add(employee_phone)
            db_session.add(guest_phone)
            db_session.flush()
            db_session.add(WifiClient(mac='AA', employee=employee, phone=employee_phone))
            db_session.add(WifiClient(mac='BB', phone=guest_phone))
            db_session.commit()

        self.assertEqual(get_credentials('AA', '79990000001')['username'], 'employee')
        self.assertEqual(get_credentials('BB', '79990000002')['username'], 'guest')

        mock_config.radius.enabled = True
        mock_generate_token.return_value = 'token'
        result = get_credentials('CC', '79990000003')
        self.assertEqual(result, {'username': 'CC', 'password': 'token'})
        mock_generate_token.assert_called_with('CC')
