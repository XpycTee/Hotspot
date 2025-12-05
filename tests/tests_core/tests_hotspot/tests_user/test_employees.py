import datetime
import unittest
from unittest.mock import patch

from sqlalchemy import select

from core import database
from core.database.models import Model
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.hotspot.user.employees import add_employee, check_employee, delete_from_employees, update_employee, update_employee_status


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
    def _add_employee(lastname: str = 'Testing', name: str = 'Test', phone_numbers: list = ['70000000001']):
        with get_session() as db_session:
            new_employee = Employee(lastname=lastname, name=name)
            db_session.add(new_employee)
            db_session.flush()

            for phone_number in phone_numbers:
                new_phone = EmployeePhone(phone_number=phone_number, employee=new_employee)
                db_session.add(new_phone)
            new_id = new_employee.id
        return new_id

    @staticmethod
    def _add_wifi_clinet(mac='00:00:00:00:00:02', is_employee=False):
        with get_session() as db_session:
            wifi_client = WifiClient(
                mac=mac, 
                expiration=datetime.datetime.now(), 
                employee=is_employee, 
                phone=None, 
                user_fp=None
            )
            db_session.add(wifi_client)
            db_session.commit()

    @patch('core.hotspot.user.employees.get_translate', return_value='ERROR_TEXT')
    def test_add_employee(self, *args):
        expected = {'status': 'OK', 'employee_id': 1}
        result = add_employee('Testing', 'Test', ['79999999901'])
        self.assertDictEqual(result, expected)

        expected = {'status': 'ALREDY_EXISTS', 'error_message': 'ERROR_TEXT'}
        result = add_employee('Testing', 'Test', ['79999999901'])
        self.assertDictEqual(result, expected)

    def test_delete_from_employees(self):
        employee_id = self._add_employee('Testing', 'Test', ['70000000001'])

        expected = {'status': 'OK'}
        result = delete_from_employees(employee_id)
        self.assertDictEqual(result, expected)

        expected = {'status': 'NOT_FOUND'}
        result = delete_from_employees(100)
        self.assertDictEqual(result, expected)

    @patch('core.hotspot.user.employees.get_translate', return_value='ERROR_TEXT')
    def test_update_employee(self, *args):
        employee_id = self._add_employee('Testing', 'Test', ['70000000001'])

        expected = {'status': 'BAD_REUQEST'}
        result = update_employee(employee_id)
        self.assertDictEqual(result, expected)

        expected = {'status': 'NOT_FOUND', 'error_message': 'ERROR_TEXT'}
        result = update_employee(100, 'NotFound', 'User')
        self.assertDictEqual(result, expected)

        expected = {'status': 'OK'}
        result = update_employee(employee_id, 'Newman', 'User', ['70000000001', '79999999901'])
        self.assertDictEqual(result, expected)
        with get_session() as db_session:
            query = select(Employee).where(Employee.id==employee_id)
            employee = db_session.scalars(query).first()
            self.assertEqual(employee.lastname, 'Newman')
            self.assertEqual(employee.name, 'User')
            self.assertListEqual(
                [phone.phone_number for phone in employee.phones], 
                ['70000000001', '79999999901']
            )

    def test_check_employee(self):
        _ = self._add_employee('Testing', 'Test', ['70000000001'])

        result = check_employee('70000000001')
        self.assertTrue(result)

        result = check_employee('70000000000')
        self.assertFalse(result)

    def test_update_employee_status(self):
        self._add_wifi_clinet('00:00:00:00:00:02', False)
        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac=='00:00:00:00:00:02')
            wifi_client = db_session.scalars(query).first()
            self.assertFalse(wifi_client.employee)

        update_employee_status('00:00:00:00:00:02', True)

        with get_session() as db_session:
            query = select(WifiClient).where(WifiClient.mac=='00:00:00:00:00:02')
            wifi_client = db_session.scalars(query).first()
            self.assertTrue(wifi_client.employee)
