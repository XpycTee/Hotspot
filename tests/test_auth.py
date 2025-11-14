import datetime
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from sqlalchemy import select

from extensions import get_translate, cache

# Add the root directory of the project to the sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
from app.pages.auth import (
    auth_bp,
    _octal_string_to_bytes,
    _check_employee,
)

from app.database import db

class TestAuthViews(unittest.TestCase):
    def setUp(self):
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
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['CACHE_TYPE'] = 'simple'

        db.init_app(self.app)
        cache.init_app(self.app)
        with self.app.app_context():
            db.create_all()

            # Добавление номера телефона в таблицу EmployeePhone
            from app.database.models import WifiClient, ClientsNumber, EmployeePhone, Blacklist  # Импорт модели EmployeePhone
            
            new_emp_client = ClientsNumber(phone_number='79999999999', last_seen=datetime.datetime.now())
            db.session.add(new_emp_client)
            db.session.commit()
            new_phone = EmployeePhone(phone_number='79999999999', employee_id=new_emp_client.id)
            db.session.add(new_phone)
            new_wifi_client = WifiClient(mac="12:34:56:78:9A:BC", expiration=datetime.datetime.now().replace(hour=23, minute=59, second=59), employee=True, phone=new_emp_client)
            db.session.add(new_wifi_client)
            db.session.commit()
            cache.set("fingerprint:e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002", new_wifi_client.mac)

            new_blocked_phone = Blacklist(phone_number='79999999123')
            db.session.add(new_blocked_phone)

            new_guest_client = ClientsNumber(phone_number='79999999321', last_seen=datetime.datetime.now())
            db.session.add(new_guest_client)
            
            db.session.commit()
            
        @self.app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_octal_string_to_bytes(self):
        self.assertEqual(_octal_string_to_bytes("\\141\\142\\143"), b'abc')

    def test_check_employee(self):
        with self.app.app_context():
            self.assertTrue(_check_employee('79999999999'))
            self.assertFalse(_check_employee('0987654321'))

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
                for key, value in test_init_data.items():
                    sess[key] = value
            response = c.post('/login')
            self.assertEqual(response.status_code, 200)

    @patch('app.pages.auth._check_employee')
    def test_login_route_bad_emp(self, mock_chck):
        mock_chck.return_value = False
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '12:34:56:78:9A:BC'
        }
        with self.client as c:
            response = c.post('/login', data=test_init_data)
            self.assertEqual(response.status_code, 200)

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
                for key, value in test_init_data.items():
                    sess[key] = value
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
                for key, value in test_init_data.items():
                    sess[key] = value
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
                for key, value in test_init_data.items():
                    sess[key] = value
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
                for key, value in test_init_data.items():
                    sess[key] = value
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="employee_pass"', response.data)

    def test_sendin_route_employee_https_fp(self):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999',
            'fingerprint': '0123456789abcdef'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                for key, value in test_init_data.items():
                    sess[key] = value
            response = c.get('/sendin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="password" value="employee_pass"', response.data)
    
    def test_code_route(self):
        test_init_data = {'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)
    
    def test_code_route_blocked(self):
        test_blocked_init_data = {'phone': '79999999123'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_blocked_init_data)
            self.assertEqual(response.status_code, 403)

    def test_code_route_mac(self):
        test_init_data = {
            'phone': '79999999999'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '12:34:56:78:9A:BC'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_fp(self):
        test_init_data = {
            'phone': '79999999999'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:FF'
                sess['hardware_fp'] = '0123456789abcdef'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_session(self):
        test_init_data = {'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '71234567890'
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    def test_resend_route_cache_code(self):
        cache.set('code:79999999999', '1234')

        mock_sender = MagicMock()
        mock_sender.send_sms.return_value = None
        self.app.config['SENDER'] = mock_sender

        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '79999999999'
            response = c.post('/resend')
            mock_sender.send_sms.assert_called_once_with('79999999999', 'Your code is 1234')
            
            self.assertEqual(response.status_code, 200)

    @patch('app.pages.auth.randint', return_value=9876)
    def test_resend_route_rnd_code(self, _):
        mock_sender = MagicMock()
        mock_sender.send_sms.return_value = None
        self.app.config['SENDER'] = mock_sender

        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '79999999999'
            response = c.post('/resend')
            mock_sender.send_sms.assert_called_once_with('79999999999', 'Your code is 9876')
            self.assertEqual(response.status_code, 200)
    
    def test_resend_route_sended(self):
        cache.set('sended:79999999999', True)
        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '79999999999'
            response = c.post('/resend')
            self.assertEqual(response.status_code, 400)

    @patch('app.pages.auth.cache')
    def test_auth_route(self, mock_cache):
        test_init_data = {'code': '1234'}
        mock_cache.get.return_value = '1234'
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
                sess['phone'] = '71234567890'
            response = c.post('/auth', data=test_init_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

    @patch('app.pages.auth.cache')
    def test_auth_route_update_client(self, mock_cache):
        test_init_data = {'code': '1234'}
        mock_cache.get.return_value = '1234'
        from app.database.models import WifiClient
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '12:34:56:78:9A:BC'
                sess['phone'] = '71234567890'
            
            db_client = db.session.execute(
                select(WifiClient).where(WifiClient.mac == sess['mac']).with_for_update()
            ).scalar_one_or_none()
            self.assertNotEqual(db_client.employee, False)
            self.assertNotEqual(db_client.phone.phone_number, sess['phone'])

            response = c.post('/auth', data=test_init_data)
                        
            self.assertEqual(response.status_code, 302)
            self.assertEqual(db_client.employee, False)
            self.assertEqual(db_client.phone.phone_number, sess['phone'])
            self.assertIn('/sendin', response.location)

    @patch('app.pages.auth.cache')
    def test_auth_route_bad_code(self, mock_cache):
        test_init_data = {'code': '1234'}
        mock_cache.get.return_value = '5678'
        expected_responses = [
            (307, '/code'),
            (307, '/code'),
            (302, '/login')
        ]

        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
                sess['phone'] = '71234567890'

            for expected_status, expected_location in expected_responses:
                response = c.post('/auth', data=test_init_data)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_location, response.location)

    def test_fp_repeating(self):
        test_init_data = {
            'mac': '00:00:00:00:00:FF',
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999',
            'hardware_fp': '0123456789abcdef'
        }
        with self.client as c:
            with c.session_transaction() as sess:
                for key, value in test_init_data.items():
                    sess[key] = value
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            response = c.post('/sendin', data=test_init_data)
            self.assertEqual(response.status_code, 200)
            
            with c.session_transaction() as sess:
                for key, value in test_init_data.items():
                    sess[key] = value
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            fp = cache.get('fingerprint:e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002')
            assert None != fp


if __name__ == '__main__':
    unittest.main()
