import datetime
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, session

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
        self.app.config['BLACKLIST'] = []
        self.app.config['HOTSPOT_USERS'] = {
            'employee': {'delay': datetime.timedelta(hours=1), 'password': 'employee_pass'},
            'guest': {'delay': datetime.timedelta(hours=1), 'password': 'guest_pass'}
        }
        self.app.config['EMPLOYEES'] = {
            'employees': [{'phone': ['79999999999']}]
        }
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

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_octal_string_to_bytes(self):
        self.assertEqual(_octal_string_to_bytes("\\141\\142\\143"), b'abc')

    @patch('app.pages.auth._load_employees')
    def test_check_employee(self, mock_load_employees):
        with self.app.app_context():
            mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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

    @patch('app.pages.auth._load_employees')
    def test_sendin_route_guest_chap(self, mock_load_employees):
        mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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

    @patch('app.pages.auth._load_employees')
    def test_sendin_route_guest_https(self, mock_load_employees):
        mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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

    @patch('app.pages.auth._load_employees')
    def test_sendin_route_employee_chap(self, mock_load_employees):
        mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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

    @patch('app.pages.auth._load_employees')
    def test_sendin_route_employee_https(self, mock_load_employees):
        mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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

    @patch('app.pages.auth.current_app', new_callable=MagicMock)
    def test_code_route(self, mock_current_app):
        test_init_data = {'phone': '71234567890'}
        mock_sender = MagicMock()
        mock_sender.send_sms.return_value = None
        mock_current_app.config.get.return_value = mock_sender
        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)

    @patch('app.pages.auth.current_app', new_callable=MagicMock)
    def test_code_route_session(self, mock_current_app):
        test_init_data = {'phone': '71234567890'}
        mock_sender = MagicMock()
        mock_sender.send_sms.return_value = None
        mock_current_app.config.get.return_value = mock_sender
        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '71234567890'
                sess['mac'] = '00:00:00:00:00:00'
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 200)
    
    @patch('app.pages.auth._load_employees')
    def test_auth_route(self, mock_load_employees):
        mock_load_employees.return_value = self.app.config.get('EMPLOYEES')
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
