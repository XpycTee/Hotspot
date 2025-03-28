import datetime
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, session

# Add the root directory of the project to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.pages.auth import (
    octal_string_to_bytes,
    check_employee,
    sendin,
    login,
    code,
    auth
)

from app.database import db

class TestAuthViews(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.debug = True
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
        self.assertEqual(octal_string_to_bytes("\\141\\142\\143"), b'abc')

    @patch('app.pages.auth.yaml.safe_load')
    @patch('app.pages.auth.os.path.getmtime')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="phone: ['1234567890']")
    def test_check_employee(self, mock_open, mock_getmtime, mock_safe_load):
        with self.app.app_context():
            mock_getmtime.return_value = time.time()
            mock_safe_load.return_value = {'employees': [{'phone': ['1234567890']}]}
            self.assertTrue(check_employee('1234567890'))
            self.assertFalse(check_employee('0987654321'))

    @patch('app.pages.auth.render_template')
    def test_login_post(self, mock_render_template):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00'
        }
        with self.app.app_context():
            with self.app.test_request_context('/login', method='POST', data=test_init_data):
                session['error'] = None
                mock_render_template.side_effect = lambda html, error: (html, error)
                response = login()
                self.assertEqual(response, ('login.html', None))

    @patch('app.pages.auth.render_template')
    def test_login_session(self, mock_render_template):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'mac': '00:00:00:00:00:00'
        }
        with self.app.app_context():
            with self.app.test_request_context('/login', method='POST'):
                for key, value in test_init_data.items():
                    session[key] = value
                session['error'] = None
                mock_render_template.side_effect = lambda html, error: (html, error)
                response = login()
                self.assertEqual(response, ('login.html', None))

    @patch('app.pages.auth.check_employee')
    @patch('app.pages.auth.render_template')
    def test_sendin_guest_chap(self, mock_render_template, mock_check_employee):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '71234567890'
        }
        with self.app.app_context():
            with self.app.test_request_context('/sendin', method='POST'):
                for key, value in test_init_data.items():
                    session[key] = value
                session['error'] = None
                mock_render_template.side_effect = lambda ret, **kwargs: (ret, kwargs)
                mock_check_employee.return_value = lambda phone: phone in self.app.config['EMPLOYEES'][0]['phone'][0]
                response = sendin()
                right_response = ('sendin.html', {
                    'username': 'employee', 
                    'password': '01cd9223b5c93047a6cb493d71d460f5', 
                    'link_login_only': 'link', 
                    'link_orig': 'orig'
                    })
                self.assertEqual(response, right_response)

    @patch('app.pages.auth.check_employee')
    @patch('app.pages.auth.render_template')
    def test_sendin_guest_https(self, mock_render_template, mock_check_employee):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '71234567890'
        }
        with self.app.app_context():
            with self.app.test_request_context('/sendin', method='POST'):
                for key, value in test_init_data.items():
                    session[key] = value
                session['error'] = None
                mock_render_template.side_effect = lambda ret, **kwargs: (ret, kwargs)
                mock_check_employee.return_value = lambda phone: phone in self.app.config['EMPLOYEES'][0]['phone'][0]
                response = sendin()
                right_response = ('sendin.html', {
                    'username': 'employee', 
                    'password': 'employee_pass', 
                    'link_login_only': 'link', 
                    'link_orig': 'orig'
                    })
                self.assertEqual(response, right_response)

    @patch('app.pages.auth.check_employee')
    @patch('app.pages.auth.render_template')
    def test_sendin_employee_chap(self, mock_render_template, mock_check_employee):
        test_init_data = {
            'chap-id': '1', 
            'chap-challenge': 'challenge', 
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999'
        }
        with self.app.app_context():
            with self.app.test_request_context('/sendin', method='POST'):
                for key, value in test_init_data.items():
                    session[key] = value
                session['error'] = None
                mock_render_template.side_effect = lambda ret, **kwargs: (ret, kwargs)
                mock_check_employee.return_value = lambda phone: phone in self.app.config['EMPLOYEES'][0]['phone'][0]
                response = sendin()
                right_response = ('sendin.html', {
                    'username': 'employee', 
                    'password': '01cd9223b5c93047a6cb493d71d460f5', 
                    'link_login_only': 'link', 
                    'link_orig': 'orig'
                    })
                self.assertEqual(response, right_response)

    @patch('app.pages.auth.check_employee')
    @patch('app.pages.auth.render_template')
    def test_sendin_employee_https(self, mock_render_template, mock_check_employee):
        test_init_data = {
            'link-login-only': 'link', 
            'link-orig': 'orig', 
            'phone': '79999999999'
        }
        with self.app.app_context():
            with self.app.test_request_context('/sendin', method='POST'):
                for key, value in test_init_data.items():
                    session[key] = value
                session['error'] = None
                mock_render_template.side_effect = lambda ret, **kwargs: (ret, kwargs)
                mock_check_employee.return_value = lambda phone: phone in self.app.config['EMPLOYEES'][0]['phone'][0]
                response = sendin()
                right_response = ('sendin.html', {
                    'username': 'employee', 
                    'password': 'employee_pass', 
                    'link_login_only': 'link', 
                    'link_orig': 'orig'
                    })
                self.assertEqual(response, right_response)

    @patch('app.pages.auth.render_template')
    @patch('app.pages.auth.current_app', new_callable=MagicMock)
    def test_code_post(self, mock_current_app, mock_render_template):
        with self.app.app_context():
            with self.app.test_request_context('/code', method='POST', data={'phone': '71234567890'}):
                session['mac'] = '00:00:00:00:00:00'
                mock_sender = MagicMock()
                mock_sender.send_sms.return_value = None
                mock_current_app.config.get.return_value = mock_sender
                mock_render_template.side_effect = lambda html, error: (html, error)
                response = code()
                self.assertEqual(response, ('code.html', None))

    @patch('app.pages.auth.render_template')
    @patch('app.pages.auth.current_app', new_callable=MagicMock)
    def test_code_session(self, mock_current_app, mock_render_template):
        with self.app.app_context():
            with self.app.test_request_context('/code', method='POST'):
                session['phone'] = '71234567890'
                session['mac'] = '00:00:00:00:00:00'
                mock_sender = MagicMock()
                mock_sender.send_sms.return_value = None
                mock_current_app.config.get.return_value = mock_sender
                mock_render_template.side_effect = lambda html, error: (html, error)
                response = code()
                self.assertEqual(response, ('code.html', None))

    @patch('app.pages.auth.url_for')
    @patch('app.pages.auth.redirect')
    @patch('app.pages.auth.models.WifiClient.query.filter_by')
    @patch('app.pages.auth.models.ClientsNumber.query.filter_by')
    def test_auth(self, mock_clients_number_filter_by, mock_wifi_client_filter_by, mock_redirect, mock_url_for):
        with self.app.app_context():
            with self.app.test_request_context('/auth', method='POST', data={'code': '1234'}):
                session['mac'] = '00:00:00:00:00:00'
                session['phone'] = '71234567890'
                session['code'] = '1234'
                mock_clients_number = MagicMock()
                mock_clients_number.phone_number = '71234567890'
                mock_clients_number_filter_by.return_value.first.return_value = mock_clients_number
                mock_wifi_client = MagicMock()
                mock_wifi_client.expiration = datetime.datetime.now() + datetime.timedelta(hours=1)
                mock_wifi_client_filter_by.return_value.first.return_value = mock_wifi_client
                mock_url_for.side_effect = lambda endpoint: endpoint
                mock_redirect.side_effect = lambda url, http_code: (url, http_code)
                response = auth()
                self.assertEqual(response, ("auth.sendin", 302))


    @patch('app.pages.auth.url_for')
    @patch('app.pages.auth.redirect')
    @patch('app.pages.auth.models.WifiClient.query.filter_by')
    @patch('app.pages.auth.models.ClientsNumber.query.filter_by')
    def test_auth_wrong_code(self, mock_clients_number_filter_by, mock_wifi_client_filter_by, mock_redirect, mock_url_for):
        with self.app.app_context():
            with self.app.test_request_context('/auth', method='POST', data={'code': '1234'}):
                session['mac'] = '00:00:00:00:00:00'
                session['phone'] = '71234567890'
                session['code'] = '5678'
                mock_clients_number = MagicMock()
                mock_clients_number.phone_number = '71234567890'
                mock_clients_number_filter_by.return_value.first.return_value = mock_clients_number
                mock_wifi_client = MagicMock()
                mock_wifi_client.expiration = datetime.datetime.now() + datetime.timedelta(hours=1)
                mock_wifi_client_filter_by.return_value.first.return_value = mock_wifi_client
                mock_url_for.side_effect = lambda endpoint: endpoint
                mock_redirect.side_effect = lambda url, http_code: (url, http_code)
                response = auth()
                self.assertEqual(response, ("auth.code", 307))
                response = auth()
                self.assertEqual(response, ("auth.code", 307))
                response = auth()
                self.assertEqual(response, ("auth.login", 302))

if __name__ == '__main__':
    unittest.main()