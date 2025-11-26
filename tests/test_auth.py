import datetime
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from sqlalchemy import select

from app.utils.language import get_translate
from core.cache import get_cache
from core.db.models import Model
from core.db.models.blacklist import Blacklist
from core.db.models.clients_number import ClientsNumber
from core.db.models.employee import Employee
from core.db.models.employee_phone import EmployeePhone
from core.db.models.wifi_client import WifiClient
from core.db.session import create_all, get_session
from core.user.repository import check_employee



# Add the root directory of the project to the sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
from app.pages.auth import (
    auth_bp,
    _octal_string_to_bytes,
)


class TestAuthViews(unittest.TestCase):
    def create_users(self):
        with get_session() as session:

            # Non Authed Employee
            non_authed_emp = Employee(lastname = "NonAuthed", name = "Employee")
            session.add(non_authed_emp)
            session.commit()
            non_authed_emp_phone = EmployeePhone(phone_number='79999999991', employee_id=non_authed_emp.id)
            session.add(non_authed_emp_phone)

            # Expired Employee
            expired_emp = Employee(lastname = "Expired", name = "Employee")
            session.add(expired_emp)
            session.commit()
            expired_emp_phone = EmployeePhone(phone_number='79999999992', employee_id=expired_emp.id)
            session.add(expired_emp_phone)
            expired_emp_client = ClientsNumber(phone_number='79999999992', last_seen=datetime.datetime.now())
            session.add(expired_emp_client)
            session.commit()
            expired_emp_wifi_client = WifiClient(mac="12:34:56:78:9A:BD", expiration=datetime.datetime.now().replace(hour=0, minute=0, second=0), employee=True, phone=expired_emp_client)
            session.add(expired_emp_wifi_client)
            session.commit()

            # Authed Employee
            authed_emp = Employee(lastname = "Authed", name = "Employee")
            session.add(authed_emp)
            session.commit()
            authed_emp_phone = EmployeePhone(phone_number='79999999999', employee_id=authed_emp.id)
            session.add(authed_emp_phone)
            authed_emp_client = ClientsNumber(phone_number='79999999999', last_seen=datetime.datetime.now())
            session.add(authed_emp_client)
            session.commit()
            authed_wifi_client = WifiClient(mac="12:34:56:78:9A:BC", expiration=datetime.datetime.now().replace(hour=23, minute=59, second=59), employee=True, phone=authed_emp_client, user_fp="e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002")
            session.add(authed_wifi_client)
            session.commit()
            
            # Expired Guest
            expired_guest_client = ClientsNumber(phone_number='70000000010', last_seen=datetime.datetime.now())
            session.add(expired_guest_client)
            session.commit()
            expired_guest_wifi_client = WifiClient(mac="00:00:00:00:00:10", expiration=datetime.datetime.now().replace(hour=0, minute=0, second=0), employee=False, phone=expired_guest_client)
            session.add(expired_guest_wifi_client)
            session.commit()

            # Authed Guest
            authed_guest_client = ClientsNumber(phone_number='70000000011', last_seen=datetime.datetime.now())
            session.add(authed_guest_client)
            session.commit()
            authed_guest_wifi_client = WifiClient(mac="00:00:00:00:00:11", expiration=datetime.datetime.now().replace(hour=23, minute=59, second=59), employee=False, phone=authed_guest_client, user_fp="ab185fb8f0baa93fc0d6852d019045d92dbc71aebec472c7461f7163892f5e92")
            session.add(authed_guest_wifi_client)
            session.commit()

            new_blocked_phone = Blacklist(phone_number='79999999123')
            session.add(new_blocked_phone)

            new_guest_client = ClientsNumber(phone_number='79999999321', last_seen=datetime.datetime.now())
            session.add(new_guest_client)

            session.commit()

    def clear_users(self):
        with get_session() as db_session:
            # очищаем все таблицы
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()

    def create_flask(self):
        self.app = Flask(__name__)
        self.app.debug = True
        self.app.register_blueprint(auth_bp)
        self.app.root_path = os.path.join(root_dir, 'app')
        self.app.config['SECRET_KEY'] = 'secret'
        self.app.config['HOTSPOT_USERS'] = {
            'employee': {'delay': datetime.timedelta(hours=1), 'password': 'employee_pass'},
            'guest': {'delay': datetime.timedelta(hours=1), 'password': 'guest_pass'}
        }
        mock_sender = MagicMock()
        mock_sender.send_sms.return_value = None
        self.app.config['SENDER'] = mock_sender
        self.app.config['LANGUAGE_DEFAULT'] = 'en'
        self.app.config['LANGUAGE_CONTENT'] = {
            'en': {
                'html': {
                    'login': {
                        'title': 'Title'
                    },
                    'code': {
                        'title': 'Title'
                    }
                },
                'sms_code': 'Your code is {code}',
                'errors': {
                    'auth': {
                        'missing_code': 'Missing code',
                        'bad_auth': 'Bad authentication',
                        'bad_code_all': 'All attempts failed',
                        'bad_code_try': 'Incorrect code, try again'
                    }
                }
            }
        }
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['CACHE_TYPE'] = 'SimpleCache'
        @self.app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)

    @classmethod
    def setUpClass(cls):
        create_all()

    def setUp(self):
        self.create_flask()
        self.create_users()
            
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.clear_users()
        self.app_context.pop()

    def test_octal_string_to_bytes(self):
        self.assertEqual(_octal_string_to_bytes("\\141\\142\\143"), b'abc')

    def test_check_employee(self):
        with self.app.app_context():
            self.assertTrue(check_employee('79999999999'))
            self.assertFalse(check_employee('0987654321'))

    def test_login_route(self):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00'
        }
        with self.client as c:
            response = c.post('/login', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    def test_login_route_nochap(self):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00'
        }
        with self.client as c:
            response = c.post('/login', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    def test_login_route_session(self):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00'
        }
        
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.post('/login')
            self.assertEqual(response.status_code, 200)

    def test_code_route(self):
        test_init_data = {'phone': '71234567890'}
        test_sess_data = {'mac': '00:00:00:00:00:00'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
                    
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)
    
    def test_code_route_blocked(self):
        test_blocked_init_data = {'phone': '79999999123'}
        test_sess_data = {'mac': '00:00:00:00:00:00'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_blocked_init_data)
            self.assertEqual(response.status_code, 403)

    def test_code_route_mac(self):
        test_init_data = {'phone': '79999999999'}
        test_sess_data = {'mac': '12:34:56:78:9A:BC'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_fp(self):
        test_init_data = {'phone': '79999999999'}
        test_sess_data = {'mac': '00:00:00:00:00:FF', 'hardware_fp': '0123456789abcdef'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_session(self):
        test_init_data = {'phone': '71234567890'}
        test_sess_data = {'mac': '00:00:00:00:00:00', 'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    def test_resend_route(self):
        cache = get_cache()
        session_id = 'test_resend_route'

        test_sess_data = {'_id': session_id, 'phone': '79999999999'}
        cache.set(f'{session_id}:sms:code', '1234')

        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/resend')
            self.assertEqual(response.status_code, 200)
    
    def test_resend_route_sended(self):
        cache = get_cache()
        session_id = 'test_resend_route_sended'
        test_sess_data = {'_id': session_id, 'phone': '79999999999'}

        cache.set(f'{session_id}:sms:sended', True)
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/resend')
            self.assertEqual(response.status_code, 400)

    @patch('app.pages.auth.authenticate_by_code', return_value={"status": "OK"})
    def test_auth_route(self, _):
        test_init_data = {'code': '1234'}
        test_sess_data = {'mac': '00:00:00:00:00:00', 'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/auth', data=test_init_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

    def test_auth_route_bad_code(self):
        cache = get_cache()
        session_id = 'test_auth_route_bad_code'
        test_init_data = {'code': '1234'}
        test_sess_data = {'_id': session_id, 'mac': '00:00:00:00:00:00', 'phone': '71234567890'}
        cache.set(f'{session_id}:sms:code', 5678)
        cache.set(f'{session_id}:sms:attempts', 0)
        expected_responses = [
            (307, '/code'),
            (307, '/code'),
            (302, '/login')
        ]

        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)

            for expected_status, expected_location in expected_responses:
                response = c.post('/auth', data=test_init_data)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_location, response.location)

    def test_sendin_route_guest_chap(self):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999321'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="40df65fa9156a1f0f72e57fe6da3d896"', response.data)

    def test_sendin_route_guest_https(self):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999321'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="guest_pass"', response.data)

    def test_sendin_route_employee_chap(self):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="01cd9223b5c93047a6cb493d71d460f5"', response.data)

    def test_sendin_route_employee_https(self):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="employee_pass"', response.data)

    def test_sendin_route_employee_https_fp(self):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999',
            'hardware_fp': '0123456789abcdef'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="employee_pass"', response.data)
    

    def test_fp_repeating(self):
        cache = get_cache()
        test_init_data = {
            'mac': '00:00:00:00:00:FF',
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999',
            'hardware_fp': '0123456789abcdef'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            response = c.post('/sendin', data=test_init_data)
            self.assertEqual(response.status_code, 200)
            
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            fp = cache.get('fingerprint:e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002')
            assert None != fp
    
    @patch('app.pages.auth.get_code', return_value="1234")
    def test_scenario_guest_code(self, _):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '71234567890'}
        test_auth_data = {'code': '1234'}

        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/auth', data=test_auth_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    def test_scenario_guest_epxiration(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:11',
            'hardware_fp': '0123456789abcdef'
        }
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    
    def test_scenario_guest_mac_phone(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:10',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '70000000010'}
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    def test_scenario_guest_fp_phone(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:XX',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '70000000011'}
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)
            
            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)
    
    @patch('app.pages.auth.randint', return_value=1234)
    def test_scenario_emp_code(self, _):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '79999999991'}
        test_auth_data = {'code': '1234'}

        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/auth', data=test_auth_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    def test_scenario_emp_epxiration(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '12:34:56:78:9A:BC',
            'hardware_fp': '0123456789abcdef'
        }
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    def test_scenario_emp_mac_phone(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '12:34:56:78:9A:BD',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '79999999992'}
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)

    def test_scenario_emp_fp_phone(self):
        test_login_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:XX',
            'hardware_fp': '0123456789abcdef'
        }
        test_code_data = {'phone': '79999999999'}
        
        with self.client as c:
            response = c.post('/login', data=test_login_data)
            self.assertEqual(response.status_code, 200)

            response = c.post('/code', data=test_code_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)
            
            response = c.post('/sendin')
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
