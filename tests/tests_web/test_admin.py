import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

from core import database
from core.cache import get_cache
from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT
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

    def setUp(self):
        self.app = self._create_flask()
        self._create_users()

        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self._clear_users()
        self.app_context.pop()
        cache = get_cache()
        cache.clear()

    @staticmethod
    def _create_flask():
        app = Flask(__name__)
        app.debug = True
        app.register_blueprint(pages_bp)
        app.root_path = os.path.join(ROOD_DIR, 'web')
        app.config['SECRET_KEY'] = 'secret'
        app.config['LANGUAGE_DEFAULT'] = LANGUAGE_DEFAULT
        app.config['LANGUAGE_CONTENT'] = LANGUAGE_CONTENT

        @app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)
        
        return app
    
    @staticmethod
    def _create_users():
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
            # очищаем все таблицы
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()

    def test_login_required_decorator(self):
        with self.client as c:
            response = c.get('/admin/')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/auth/login', response.location)
    
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
                sess['is_authenticated'] = True
            response = c.get('/admin/panel')
            self.assertEqual(response.status_code, 200)

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
                    sess['is_authenticated'] = True
                response = c.post(f'/admin/tables/{table_name}/delete', json=data)
                self.assertEqual(response.status_code, 200)
