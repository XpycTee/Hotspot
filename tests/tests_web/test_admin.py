import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

from core.admin.repository import create_user
from core import database
from core.config import get_config, init_config
from core.redis import get_cache
from core.database.models import Model
from core.database.models.blacklist import Blacklist
from core.database.models.employee import Employee
from core.database.session import get_session
from core.utils.language import get_translate
from web.pages import pages_bp


ROOD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, ROOD_DIR)


class TestAdminViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()
        init_config('web')

    def setUp(self):
        self._clear_users()
        self.app = self._create_flask()
        self._create_users()

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self._clear_users()
        self.app_context.pop()
        with get_cache() as cache:
            cache.clear()

    @staticmethod
    def _create_flask():
        app = Flask(__name__)
        app.debug = True
        app.register_blueprint(pages_bp)
        app.root_path = os.path.join(ROOD_DIR, 'web')
        app.config['SECRET_KEY'] = 'secret'
        config = get_config()
        app.config['LANGUAGE_DEFAULT'] = config.language.name
        app.config['LANGUAGE_CONTENT'] = config.language.content

        @app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)
        @app.context_processor
        def inject_get_config():
            return dict(get_config=get_config)
        
        return app
    
    @staticmethod
    def _create_users():
        create_user('admin', 'admin', 'full')
        create_user('writer', 'writer', 'write')
        create_user('reader', 'reader', 'read')
        with get_session() as db_session:
            # Add an employee
            employee = Employee(lastname='Doe', name='John')
            db_session.add(employee)
            
            # Add a phone number to the blacklist
            blacklist_entry = Blacklist(phone_number='1234567890')
            db_session.add(blacklist_entry)
            db_session.commit()

    @staticmethod
    def _clear_users():
        with get_session() as db_session:
            for table in reversed(Model.metadata.sorted_tables):
                if table.name == 'system_config':
                    continue
                db_session.execute(table.delete())
            db_session.commit()

    def test_login_required_decorator(self):
        with self.client as c:
            response = c.get('/admin')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/panel', response.location)
    
    def test_login_route(self):
        with self.client as c:
            response = c.get('/admin/auth/login')
            self.assertEqual(response.status_code, 200)

    def test_auth_success(self):
        with self.client as c:
            response = c.post('/admin/auth/check', data={'username': 'admin', 'password': 'admin'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/panel', response.location)

    def test_auth_failure(self):
        with self.client as c:
            response = c.post('/admin/auth/check', data={'username': 'admin', 'password': 'wrong_pass'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/auth/login', response.location)

    @patch('web.pages.admin.auth.login_by_password', return_value={'status': 'LOCKOUT'})
    def test_auth_lockout(self, _):
        with self.client as c:
            response = c.post('/admin/auth/check', data={'username': 'admin', 'password': 'wrong_pass'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/auth/login', response.location)
    
    def test_panel_route(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['username'] = 'admin'
                sess['is_authenticated'] = True
            response = c.get('/admin/panel')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/panel/wifi-clients', response.location)

    def test_logout_route(self):
        with self.client as c:
            response = c.get('/admin/auth/logout')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/auth/login', response.location)

    def test_save_route(self):
        table_data = {
            "employees": {"id": 1, 'lastname': 'Newnamen'},
            "blacklist": {"phone": "0987654321"}
        }
        for table_name, data in table_data.items():
            with self.client as c:
                with c.session_transaction() as sess:
                    sess['username'] = 'admin'
                    sess['is_authenticated'] = True
                response = c.post(f'/admin/tables/{table_name}/save', json=data)
                self.assertEqual(response.status_code, 200)

    def test_delete_route(self):
        table_data = {
            "employees": {"id": 1},
            "blacklist": {"phone": "1234567890"}
        }
        for table_name, data in table_data.items():
            with self.client as c:
                with c.session_transaction() as sess:
                    sess['username'] = 'admin'
                    sess['is_authenticated'] = True
                response = c.post(f'/admin/tables/{table_name}/delete', json=data)
                self.assertEqual(response.status_code, 200)

    def test_acl_read_group(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['username'] = 'reader'
                sess['is_authenticated'] = True

            allowed = [
                ('get', '/admin/panel/wifi-clients', None, {200}),
                ('get', '/admin/tables/wifi_clients', None, {200}),
            ]
            forbidden = [
                ('get', '/admin/panel/employees'),
                ('get', '/admin/panel/blacklist'),
                ('post', '/admin/tables/employees/save', {'lastname': 'A', 'name': 'B', 'phone': ['70000000000']}),
                ('post', '/admin/tables/blacklist/save', {'phone': '79998887766'}),
                ('post', '/admin/hotspot/deauth', {'mac': '00:11:22:33:44:55'}),
                ('post', '/admin/hotspot/block', {'mac': '00:11:22:33:44:55'}),
                ('get', '/admin/settings'),
            ]

            for method, url, payload, expected_codes in allowed:
                response = c.get(url) if method == 'get' else c.post(url, json=payload)
                self.assertIn(response.status_code, expected_codes)

            for method, url, *payload in forbidden:
                response = c.get(url) if method == 'get' else c.post(url, json=payload[0])
                self.assertEqual(response.status_code, 403)

    def test_acl_write_group(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['username'] = 'writer'
                sess['is_authenticated'] = True

            allowed = [
                ('get', '/admin/panel/wifi-clients', None, {200}),
                ('get', '/admin/panel/employees', None, {200}),
                ('get', '/admin/panel/blacklist', None, {200}),
                ('get', '/admin/tables/wifi_clients', None, {200}),
                ('post', '/admin/tables/employees/save', {'lastname': 'A', 'name': 'B', 'phone': ['70000000000']}, {200}),
                ('post', '/admin/tables/blacklist/save', {'phone': '79998887766'}, {200}),
                ('post', '/admin/hotspot/deauth', {'mac': '00:11:22:33:44:55'}, {200}),
                ('post', '/admin/hotspot/block', {'mac': '00:11:22:33:44:55'}, {404}),
            ]
            forbidden = [
                ('get', '/admin/settings'),
                ('get', '/admin/settings/users'),
                ('post', '/admin/settings/users/update', {'id': 'reader', 'fields': {'group': 'write'}}),
            ]

            for method, url, payload, expected_codes in allowed:
                response = c.get(url) if method == 'get' else c.post(url, json=payload)
                self.assertIn(response.status_code, expected_codes)

            for method, url, *payload in forbidden:
                response = c.get(url) if method == 'get' else c.post(url, json=payload[0])
                self.assertEqual(response.status_code, 403)
