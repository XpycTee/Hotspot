import os
import sys
import unittest
from unittest import mock
from unittest.mock import patch

import bcrypt
from flask import Flask

# Add the root directory of the project to the sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)
from app.database.models import Blacklist, Employee
from app.pages.admin import (
    admin_bp,
    _check_password,
    _reset_login_attempts,
    _handle_failed_login
)

from app.database import db
from extensions import get_translate

class TestAdminViews(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(admin_bp)
        self.app.root_path = os.path.join(root_dir, 'app')
        self.app.config['SECRET_KEY'] = 'secret'
        self.app.config['BLACKLIST'] = []
        self.app.config['ADMIN'] = {'username': 'admin', 'password': bcrypt.hashpw('admin_pass'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')}
        self.app.config['EMPLOYEES'] = {}
        self.app.config['MAX_LOGIN_ATTEMPTS'] = 3
        self.app.config['LOCKOUT_TIME'] = 5
        self.app.config['LANGUAGE_CONTENT'] = {
            'html': {
                'login': {
                    'title': 'Title'
                }
            },
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
        @self.app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)
        
        with self.app.app_context():
            db.create_all()
            
            # Add an employee
            employee = Employee(lastname='Doe', name='John')
            db.session.add(employee)
            
            # Add a phone number to the blacklist
            blacklist_entry = Blacklist(phone_number='1234567890')
            db.session.add(blacklist_entry)
            
            # Commit the session to save changes
            db.session.commit()

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_login_required_decorator(self):
        with self.client as c:
            response = c.get('/admin/')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login', response.location)
    
    def test_login_route(self):
        with self.client as c:
            response = c.get('/admin/login')
            self.assertEqual(response.status_code, 200)

    @patch('app.pages.admin.cache')
    def test_auth_success(self, mock_cache):
        with self.client as c:
            response = c.post('/admin/auth', data={'username': 'admin', 'password': 'admin_pass'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/panel', response.location)

    @patch('app.pages.admin.cache')
    def test_auth_failure(self, mock_cache):
        with self.client as c:
            mock_cache.get.return_value = 0
            response = c.post('/admin/auth', data={'username': 'admin', 'password': 'wrong_pass'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login', response.location)

    @patch('app.pages.admin.cache')
    def test_auth_lockout(self, mock_cache):
        mock_cache.get.side_effect = [2, None, None]  # Simulate 2 failed attempts
        with self.client as c:
            response = c.post('/admin/auth', data={'username': 'admin', 'password': 'wrong_pass'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login', response.location)
    
    def test_panel_route(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['is_authenticated'] = True
            response = c.get('/admin/panel')
            self.assertEqual(response.status_code, 200)

    def test_logout_route(self):
        with self.client as c:
            response = c.get('/admin/logout')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login', response.location)

    def test_check_password(self):
        hashed_password = self.app.config['ADMIN']['password']
        self.assertTrue(_check_password('admin_pass', hashed_password))
        self.assertFalse(_check_password('wrong_pass', hashed_password))

    @patch('app.pages.admin.cache')
    def test_reset_login_attempts(self, mock_cache):
        _reset_login_attempts()
        mock_cache.delete.assert_any_call("login_attempts")
        mock_cache.delete.assert_any_call("lockout_until")

    @patch('app.pages.admin.cache')
    def test_handle_failed_login(self, mock_cache):
        with self.app.test_request_context('/admin/auth'):
            for i in range(3):
                mock_cache.get.return_value = i
                _handle_failed_login('admin', '127.0.0.1')
                if i < 2:
                    mock_cache.set.assert_any_call("login_attempts", i+1, timeout=300)
                else:
                    mock_cache.set.assert_any_call("lockout_until", mock.ANY, timeout=300)

    def test_save_route(self):
        table_data = {
            "employee": {"id": 1},
            "blacklist": {"phone": "1234567890"}
        }
        for table_name, data in table_data.items():
            with self.client as c:
                with c.session_transaction() as sess:
                    sess['is_authenticated'] = True
                response = c.post(f'/admin/delete/{table_name}', json=data)
                self.assertEqual(response.status_code, 200)

    def test_delete_route(self):
        table_data = {
            "employee": {"id": 1},
            "blacklist": {"phone": "1234567890"}
        }
        for table_name, data in table_data.items():
            with self.client as c:
                with c.session_transaction() as sess:
                    sess['is_authenticated'] = True
                response = c.post(f'/admin/delete/{table_name}', json=data)
                self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
    