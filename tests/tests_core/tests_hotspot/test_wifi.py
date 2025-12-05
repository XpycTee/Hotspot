import datetime
import unittest
from unittest.mock import patch

from sqlalchemy import select

from core import database
from core.cache import get_cache
from core.database.models import Model
from core.database.models.blacklist import Blacklist
from core.database.models.clients_number import ClientsNumber
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.wifi.auth import authenticate_by_code, authenticate_by_mac, authenticate_by_phone, get_credentials
from core.hotspot.wifi.challange import _octal_string_to_bytes, hash_chap, radius_check_chap
from core.hotspot.wifi.fingerprint import hash_fingerprint, update_fingerprint
from core.hotspot.wifi.repository import create_or_udpate_wifi_client, find_by_fp, find_by_mac
from core.utils.language import get_translate


class TestCoreHotpsotWiFi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()

    def tearDown(self):
        self._clear_users()
    
    @staticmethod
    def _clear_users():
        with get_session() as db_session:
            # очищаем все таблицы
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()

    @staticmethod
    def _create_db_user_fp(mac=None, user_fp=None):
        if not mac:
            mac = '00:00:00:00:00:01'

        if not user_fp:
            user_fp = 'qwerty'

        with get_session() as db_session:
            wifi_client = WifiClient(mac='00:00:00:00:00:01', user_fp='qwerty')
            db_session.add(wifi_client)
            db_session.commit()

    @staticmethod
    def _db_non_authed_emp(phone_number=None):
        if not phone_number:
            phone_number = '79990000000'

        with get_session() as db_session:
            non_authed_emp = Employee(
                lastname = 'NonAuthed', 
                name = 'Employee'
            )
            db_session.add(non_authed_emp)
            db_session.commit()

            non_authed_emp_phone = EmployeePhone(
                phone_number=phone_number, 
                employee_id=non_authed_emp.id
            )
            db_session.add(non_authed_emp_phone)
            db_session.commit()
    
    @staticmethod
    def _db_expired_emp(mac=None, phone_number=None, user_fp=None):
        if not mac:
            mac = 'AA:AA:AA:00:00:01'

        if not phone_number:
            phone_number = '79990000001'

        with get_session() as db_session:
            expired_emp = Employee(
                lastname = 'Expired', 
                name = 'Employee'
            )
            db_session.add(expired_emp)
            db_session.commit()

            expired_emp_phone = EmployeePhone(
                phone_number=phone_number, 
                employee_id=expired_emp.id
            )
            db_session.add(expired_emp_phone)

            expired_emp_client = ClientsNumber(
                phone_number=phone_number, 
                last_seen=datetime.datetime.now()
            )
            db_session.add(expired_emp_client)
            db_session.commit()

            expired_emp_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime(1970, 1, 1), 
                employee=True, 
                phone=expired_emp_client,
                user_fp=user_fp
            )
            db_session.add(expired_emp_wifi_client)
            db_session.commit()
    
    @staticmethod
    def _db_authed_emp(mac=None, phone_number=None, user_fp=None):
        if not mac:
            mac = 'AA:AA:AA:00:00:02'

        if not phone_number:
            phone_number = '79990000002'

        if not user_fp:
            user_fp = 'f344ea5b5b42f07f8885f6e154aa6d30e558d13ad7d3459611cdf410d42e1972'

        with get_session() as db_session:
            authed_emp = Employee(
                lastname = 'Authed', name = 'Employee'
            )
            db_session.add(authed_emp)
            db_session.commit()
            authed_emp_phone = EmployeePhone(
                phone_number=phone_number, 
                employee_id=authed_emp.id
            )
            db_session.add(authed_emp_phone)
            authed_emp_client = ClientsNumber(
                phone_number=phone_number, 
                last_seen=datetime.datetime.now()
            )
            db_session.add(authed_emp_client)
            db_session.commit()
            authed_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime.now() + datetime.timedelta(days=30), 
                employee=True, 
                phone=authed_emp_client, 
                user_fp=user_fp
            )
            db_session.add(authed_wifi_client)
            db_session.commit()

    @staticmethod
    def _db_expired_guest(mac=None, phone_number=None, user_fp=None):
        if not mac:
            mac = '00:00:00:00:00:01'

        if not phone_number:
            phone_number = '70000000001'

        with get_session() as db_session:
            expired_guest_client = ClientsNumber(
                phone_number=phone_number, 
                last_seen=datetime.datetime.now()
            )
            db_session.add(expired_guest_client)
            db_session.commit()
            expired_guest_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime(1970, 1, 1), 
                employee=False, 
                phone=expired_guest_client,
                user_fp=user_fp
            )
            db_session.add(expired_guest_wifi_client)
            db_session.commit()
    
    @staticmethod
    def _db_authed_guest(mac=None, phone_number=None, user_fp=None):
        if not mac:
            mac = '00:00:00:00:00:02'

        if not phone_number:
            phone_number = '70000000002'

        if not user_fp:
            user_fp = '73d6746e649daf41416b5b678b44e3818ae49fcd4f81a6ce7c87d98707a9b144'

        with get_session() as db_session:
            authed_guest_client = ClientsNumber(
                phone_number=phone_number, 
                last_seen=datetime.datetime.now()
            )
            db_session.add(authed_guest_client)
            db_session.commit()
            authed_guest_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime.now() + datetime.timedelta(days=1), 
                employee=False, 
                phone=authed_guest_client, 
                user_fp=user_fp
            )
            db_session.add(authed_guest_wifi_client)
            db_session.commit()

    @staticmethod
    def _db_phoneless(mac=None):
        if not mac:
            mac = '00:00:00:00:00:03'

        with get_session() as db_session:
            phoneless_wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime.now() + datetime.timedelta(days=1), 
                employee=False, 
                phone=None, 
                user_fp=None
            )
            db_session.add(phoneless_wifi_client)
            db_session.commit()

    @staticmethod
    def _db_blocked(mac=None, phone_number=None):
        if not mac:
            mac = '00:00:00:00:00:04'

        if not phone_number:
            phone_number = '70000000004'

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

            new_blocked_phone = Blacklist(phone_number=phone_number)
            db_session.add(new_blocked_phone)
            db_session.commit()

    @staticmethod
    def _db_wtf_TODO(): # TODO Кто и для чего это?
        with get_session() as db_session:
            new_guest_client = ClientsNumber(
                phone_number='70000000009', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(new_guest_client)
            db_session.commit()

    def test_radius_check_chap(self):
        chap_id = b'\x00'
        chap_challenge = b'\x00\x01\x02\x03\x04\x05\x06\x07'
        hash_password = b'\xa8\xd3\x16(c\xbd}\xa4>\x8c\x85$.\xb7\xe18'
        good_password = 'secret'
        bad_password = 'qwertyuiop'

        result = radius_check_chap(chap_id+hash_password, chap_challenge, good_password)
        self.assertTrue(result)

        result = radius_check_chap(chap_id+hash_password, chap_challenge, bad_password)
        self.assertFalse(result)

    def test_octal_string_to_bytes(self):
        self.assertEqual(_octal_string_to_bytes('\\141\\142\\143'), b'abc')

    def test_hash_chap(self):
        chap_id = '\\000'
        chap_challenge = '\\141\\142\\143'
        password = 'secret'
        expected_hash_password = 'fddec1a3b42bee03237261fa3ad2f8bb'

        hash_password = hash_chap(chap_id, password, chap_challenge)

        self.assertEqual(hash_password, expected_hash_password)

    def test_hash_fingerprint(self):
        phone_number = '79999999999'
        hardware_fp = '0123456789abcdef'
        expected = 'e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002'

        result = hash_fingerprint(phone_number, hardware_fp)
        self.assertEqual(result, expected)

    def test_update_fingerprint(self):
        self._create_db_user_fp()
        
        mac = '00:00:00:00:00:01'
        old_fp = 'qwerty'
        new_fp = '0123456789abcdef'

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac==mac)
            wifi_client = db_session.scalars(query).first()
            self.assertEqual(wifi_client.user_fp, old_fp)

        update_fingerprint(mac, new_fp)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac==mac)
            wifi_client = db_session.scalars(query).first()
            self.assertEqual(wifi_client.user_fp, new_fp)

    def test_find_by_mac(self):
        self._create_db_user_fp()

        mac = '00:00:00:00:00:01'
        expected = {
            'mac': '00:00:00:00:00:01',
            'expiration': None,
            'employee': None,
            'phone': None
        }

        result = find_by_mac(mac)

        self.assertEqual(result, expected)

    def test_find_by_fp(self):
        self._create_db_user_fp()

        user_fp = 'qwerty'
        expected = {
            'mac': '00:00:00:00:00:01',
            'expiration': None,
            'employee': None,
            'phone': None
        }

        result = find_by_fp(user_fp)

        self.assertEqual(result, expected)

    def test_create_or_udpate_wifi_client(self):
        mac = 'FF:FF:FF:00:00:01'

        new_is_employee = False
        new_phone_number = '79999990001'

        update_is_employee = True
        update_phone_number = '79999990002'

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac==mac)
            wifi_client = db_session.scalars(query).first()
            self.assertIsNone(wifi_client)

        create_or_udpate_wifi_client(mac, new_is_employee, new_phone_number)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac==mac)
            wifi_client = db_session.scalars(query).first()
            self.assertIsNotNone(wifi_client)
            self.assertEqual(wifi_client.employee, new_is_employee)
            self.assertEqual(wifi_client.phone.phone_number, new_phone_number)

        create_or_udpate_wifi_client(mac, update_is_employee, update_phone_number)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac==mac)
            wifi_client = db_session.scalars(query).first()
            self.assertIsNotNone(wifi_client)
            self.assertEqual(wifi_client.employee, update_is_employee)
            self.assertEqual(wifi_client.phone.phone_number, update_phone_number)

    def test_authenticate_by_mac(self):
        self._db_expired_emp('AA:AA:AA:00:00:01')
        expected = {'status': 'EXPIRED'}
        result = authenticate_by_mac('AA:AA:AA:00:00:01')
        self.assertDictEqual(result, expected)

        self._db_expired_guest('00:00:00:00:00:01')
        expected = {'status': 'EXPIRED'}
        result = authenticate_by_mac('00:00:00:00:00:01')
        self.assertDictEqual(result, expected)

        self._db_blocked('00:00:00:00:00:04', '70000000004')
        expected = {'status': 'BLOCKED'}
        result = authenticate_by_mac('00:00:00:00:00:04')
        self.assertDictEqual(result, expected)

        self._db_phoneless('00:00:00:00:00:03')
        expected = {'status': 'NOT_FOUND'}
        result = authenticate_by_mac('00:00:00:00:00:03')
        self.assertDictEqual(result, expected)

        result = authenticate_by_mac('FF:FF:FF:FF:FF:FF')
        self.assertDictEqual(result, expected)

        self._db_authed_emp('AA:AA:AA:00:00:02', '79990000002', 'f344ea5b5b42f07f8885f6e154aa6d30e558d13ad7d3459611cdf410d42e1972')
        expected = {
                'status': 'OK', 
                'phone': '79990000002', 
                'mac': 'AA:AA:AA:00:00:02', 
                'user_fp': 'f344ea5b5b42f07f8885f6e154aa6d30e558d13ad7d3459611cdf410d42e1972', 
                'employee': True
            }
        result = authenticate_by_mac('AA:AA:AA:00:00:02', 'abcdef02')
        self.assertDictEqual(result, expected)

        self._db_authed_guest('00:00:00:00:00:02', '70000000002', '73d6746e649daf41416b5b678b44e3818ae49fcd4f81a6ce7c87d98707a9b144')
        expected = {
                'status': 'OK', 
                'phone': '70000000002', 
                'mac': '00:00:00:00:00:02', 
                'user_fp': '73d6746e649daf41416b5b678b44e3818ae49fcd4f81a6ce7c87d98707a9b144', 
                'employee': False
            }
        result = authenticate_by_mac('00:00:00:00:00:02', '12345602')
        self.assertDictEqual(result, expected)

    def test_authenticate_by_phone(self):
        self._db_blocked('00:00:00:00:00:04', '70000000004')
        expected = {'status': 'BLOCKED'}
        result = authenticate_by_phone('00:00:00:00:00:04', '70000000004')
        self.assertDictEqual(result, expected)
        
        self._db_phoneless('00:00:00:00:00:03')
        expected = {'status': 'NOT_FOUND'}
        result = authenticate_by_phone('00:00:00:00:00:03', '70000000003')
        self.assertDictEqual(result, expected)

        result = authenticate_by_phone('FF:FF:FF:FF:FF:FF', '79999999999')
        self.assertDictEqual(result, expected)

        # By Mac

        self._db_expired_emp('AA:AA:AA:00:00:01', '79990000001')
        expected = {
            'status': 'OK', 
            'phone': '79990000001', 
            'mac': 'AA:AA:AA:00:00:01', 
            'user_fp': None, 
            'employee': True
        }
        result = authenticate_by_phone('AA:AA:AA:00:00:01', '79990000001')
        self.assertDictEqual(result, expected)

        self._db_expired_guest('00:00:00:00:00:01', '70000000001')
        expected = {
            'status': 'OK', 
            'phone': '70000000001', 
            'mac': '00:00:00:00:00:01', 
            'user_fp': None, 
            'employee': False
        }
        result = authenticate_by_phone('00:00:00:00:00:01', '70000000001')
        self.assertDictEqual(result, expected)
        self._clear_users()

        # By Fingerprint

        self._db_expired_emp('AA:AA:AA:00:00:01', '79990000001', 'ebbca9da97239a14180e102968d96db2c316bf32c5a8b680542f381678ec773d')
        expected = {
            'status': 'OK', 
            'phone': '79990000001', 
            'mac': 'AA:AA:AA:00:00:01', 
            'user_fp': 'ebbca9da97239a14180e102968d96db2c316bf32c5a8b680542f381678ec773d', 
            'employee': True
        }
        result = authenticate_by_phone('AA:AA:AA:FF:FF:01', '79990000001', 'abcdef01')
        self.assertDictEqual(result, expected)

        self._db_expired_guest('00:00:00:00:00:01', '70000000001', '186db641a10fb5522bf40c7e65e59cf0dde326f08651303e2a671773e7034aa9')
        expected = {
            'status': 'OK', 
            'phone': '70000000001', 
            'mac': '00:00:00:00:00:01', 
            'user_fp': '186db641a10fb5522bf40c7e65e59cf0dde326f08651303e2a671773e7034aa9', 
            'employee': False
        }
        result = authenticate_by_phone('00:00:00:FF:FF:01', '70000000001', '12345601')
        self.assertDictEqual(result, expected)

    @patch('core.hotspot.wifi.auth.get_translate', return_value='ERROR_TEXT')
    @patch('core.hotspot.wifi.auth.verify_code')
    def test_authenticate_by_code(self, mock_verify_code, *args):
        session_id = '00_test_authenticate_by_code'

        mock_verify_code.return_value = None
        expected = {'status': 'CODE_EXPIRED', 'error_message': 'ERROR_TEXT'}
        result = authenticate_by_code(session_id, None, None, None)
        self.assertDictEqual(result, expected)

        mock_verify_code.return_value = True
        expected = {'status': 'OK'}
        result = authenticate_by_code(session_id, 'FF:FF:FF:FF:FF:01', '1234', '79999999901')
        self.assertDictEqual(result, expected)

        mock_verify_code.return_value = False
        for _ in range(2):
            expected = {'status': 'BAD_TRY', 'error_message': 'ERROR_TEXT'}
            result = authenticate_by_code(session_id, None, None, None)
            self.assertDictEqual(result, expected)

        expected = {'status': 'BAD_CODE', 'error_message': 'ERROR_TEXT'}
        result = authenticate_by_code(session_id, None, None, None)
        self.assertDictEqual(result, expected)
    
    @patch('core.hotspot.wifi.auth.secrets')
    @patch('core.hotspot.wifi.auth.RADIUS_ENABLED')
    def test_get_credentials(self, mock_radius_enabled, mock_secrets):
        cache = get_cache()
        staff_mac = 'AA:AA:AA:00:00:02'
        staff_phone = '79990000002'
        guest_mac = '00:00:00:00:00:02'
        guest_phone = '70000000002'


        mock_radius_enabled.__bool__.return_value = False

        self._db_authed_emp(staff_mac, staff_phone)
        expected = {'username': 'employee', 'password': 'supersecret'}
        result = get_credentials(staff_mac, staff_phone)
        self.assertDictEqual(result, expected)

        self._db_authed_guest(guest_mac, guest_phone)
        expected = {'username': 'guest', 'password': 'secret'}
        result = get_credentials(guest_mac, guest_phone)
        self.assertDictEqual(result, expected)


        mock_radius_enabled.__bool__.return_value = True
        mock_token = 'a' * 64
        mock_secrets.token_hex.return_value = mock_token

        expected = {'username': staff_phone, 'password': mock_token}
        result = get_credentials(staff_mac, staff_phone)
        self.assertDictEqual(result, expected)
        self.assertEqual(mock_token, cache.get(f'auth:token:{staff_phone}'))

        expected = {'username': guest_phone, 'password': mock_token}
        result = get_credentials(guest_mac, guest_phone)
        self.assertDictEqual(result, expected)
        self.assertEqual(mock_token, cache.get(f'auth:token:{guest_phone}'))
