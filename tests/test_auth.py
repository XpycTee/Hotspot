import datetime
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, session

from extensions import get_translate

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
        self.app.config['LANGUAGE_CONTENT'] = {
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
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()

            # Добавление номера телефона в таблицу EmployeePhone
            from app.database.models import EmployeePhone, Blacklist  # Импорт модели EmployeePhone
            new_phone = EmployeePhone(phone_number='79999999999', employee_id=1000)
            db.session.add(new_phone)
            new_blocked_phone = Blacklist(phone_number='79999999123')
            db.session.add(new_blocked_phone)
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

    def test_sendin_route_guest_chap(self):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '71234567890'
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
            'phone': '71234567890'
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

    def test_code_route(self):
        test_init_data = {'phone': '71234567890'}
        test_blocked_init_data = {'phone': '79999999123'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)

            # Test blocked phone
            response = c.post('/code', data=test_blocked_init_data)
            self.assertEqual(response.status_code, 403)
    
    def test_code_route_session(self):
        test_init_data = {'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '71234567890'
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    def test_auth_route(self):
        test_init_data = {'code': '1234'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
                sess['phone'] = '71234567890'
                sess['code'] = '1234'
            response = c.post('/auth', data=test_init_data)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/sendin', response.location)

    def test_auth_route_failure(self):
        test_init_data = {'code': '1234'}
        expected_responses = [
            (307, '/code'),
            (307, '/code'),
            (302, '/login')
        ]

        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
                sess['phone'] = '71234567890'
                sess['code'] = '5678'

            for expected_status, expected_location in expected_responses:
                response = c.post('/auth', data=test_init_data)
                self.assertEqual(response.status_code, expected_status)
                self.assertIn(expected_location, response.location)


if __name__ == '__main__':
    unittest.main()
