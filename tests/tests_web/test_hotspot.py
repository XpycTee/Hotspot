import datetime
import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask
from sqlalchemy import select

from core import database
from core.cache import get_cache
from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT
from core.database.models import Model
from core.database.models.blacklist import Blacklist
from core.database.models.clients_number import ClientsNumber
from core.database.models.employee import Employee
from core.database.models.employee_phone import EmployeePhone
from core.database.models.wifi_client import WifiClient
from core.database.session import get_session
from core.utils.language import get_translate
from web.pages import pages_bp


ROOD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, ROOD_DIR)


class TestHotspotViews(unittest.TestCase):
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
            # Non Authed Employee
            non_authed_emp = Employee(
                lastname = "NonAuthed", 
                name = "Employee"
            )
            db_session.add(non_authed_emp)
            db_session.commit()
            non_authed_emp_phone = EmployeePhone(
                phone_number='79999999991', 
                employee_id=non_authed_emp.id
            )
            db_session.add(non_authed_emp_phone)

            # Expired Employee
            expired_emp = Employee(
                lastname = "Expired", 
                name = "Employee"
            )
            db_session.add(expired_emp)
            db_session.commit()
            expired_emp_phone = EmployeePhone(
                phone_number='79999999992', 
                employee_id=expired_emp.id
            )
            db_session.add(expired_emp_phone)
            expired_emp_client = ClientsNumber(
                phone_number='79999999992', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(expired_emp_client)
            db_session.commit()
            expired_emp_wifi_client = WifiClient(
                mac="12:34:56:78:9A:BD", 
                expiration=datetime.datetime(1970, 1, 1), 
                employee=True, 
                phone=expired_emp_client
            )
            db_session.add(expired_emp_wifi_client)
            db_session.commit()

            # Authed Employee
            authed_emp = Employee(
                lastname = "Authed", name = "Employee"
            )
            db_session.add(authed_emp)
            db_session.commit()
            authed_emp_phone = EmployeePhone(
                phone_number='79999999999', 
                employee_id=authed_emp.id
            )
            db_session.add(authed_emp_phone)
            authed_emp_client = ClientsNumber(
                phone_number='79999999999', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(authed_emp_client)
            db_session.commit()
            authed_wifi_client = WifiClient(
                mac="12:34:56:78:9A:BC", 
                expiration=datetime.datetime.now() + datetime.timedelta(days=30), 
                employee=True, 
                phone=authed_emp_client, 
                user_fp="e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002"
            )
            db_session.add(authed_wifi_client)
            db_session.commit()
            
            # Expired Guest
            expired_guest_client = ClientsNumber(
                phone_number='70000000010', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(expired_guest_client)
            db_session.commit()
            expired_guest_wifi_client = WifiClient(
                mac="00:00:00:00:00:10", 
                expiration=datetime.datetime(1970, 1, 1), 
                employee=False, 
                phone=expired_guest_client
            )
            db_session.add(expired_guest_wifi_client)
            db_session.commit()

            # Authed Guest
            authed_guest_client = ClientsNumber(
                phone_number='70000000011', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(authed_guest_client)
            db_session.commit()
            authed_guest_wifi_client = WifiClient(
                mac="00:00:00:00:00:11", 
                expiration=datetime.datetime.now() + datetime.timedelta(days=1), 
                employee=False, 
                phone=authed_guest_client, 
                user_fp="ab185fb8f0baa93fc0d6852d019045d92dbc71aebec472c7461f7163892f5e92"
            )
            db_session.add(authed_guest_wifi_client)
            db_session.commit()

            new_blocked_phone = Blacklist(phone_number='79999999123')
            db_session.add(new_blocked_phone)

            new_guest_client = ClientsNumber(
                phone_number='79999999321', 
                last_seen=datetime.datetime.now()
            )
            db_session.add(new_guest_client)

            db_session.commit()

    @staticmethod
    def _clear_users():
        with get_session() as db_session:
            # очищаем все таблицы
            for table in reversed(Model.metadata.sorted_tables):
                db_session.execute(table.delete())
            db_session.commit()

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

    def test_code_route_mac_authed(self):
        test_init_data = {'phone': '79999999999'}
        test_sess_data = {'mac': '12:34:56:78:9A:BC'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_fp_authed(self):
        test_init_data = {'phone': '79999999999'}
        test_sess_data = {'mac': '00:00:00:00:00:FF', 'hardware_fp': '0123456789abcdef'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

    def test_code_route_session(self):
        test_sess_data = {'mac': '00:00:00:00:00:00', 'phone': '71234567890'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/code')
            self.assertEqual(response.status_code, 200)

    def test_resend_route(self):
        cache = get_cache()
        session_id = 'test_resend_route'

        test_sess_data = {'_id': session_id, 'phone': '79999999999'}
        cache.set(f'sms:code:{session_id}', '1234')

        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/resend')
            self.assertEqual(response.status_code, 200)
    
    def test_resend_route_sended(self):
        cache = get_cache()
        session_id = 'test_resend_route_sended'
        test_sess_data = {'_id': session_id, 'phone': '79999999999'}

        cache.set(f'sms:sended:{session_id}', True)
        with self.client as c:
            with c.session_transaction() as sess:
                sess.update(test_sess_data)
            response = c.post('/resend')
            self.assertEqual(response.status_code, 400)

    @patch('web.pages.hotspot.authenticate_by_code', return_value={"status": "OK"})
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
        cache.set(f'sms:code:{session_id}', 5678)
        cache.set(f'sms:attempts:{session_id}', 0)
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
                sess.update(test_init_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            response = c.post('/sendin', data=test_init_data)
            self.assertEqual(response.status_code, 200)
            
            with c.session_transaction() as sess:
                sess.update(test_init_data)
            response = c.post('/code', data=test_init_data)
            self.assertEqual(response.status_code, 302)

            user_fp = "e627ce00cc456a84bf2a2071bad08db1ba48fcb8bd6865a0346c6f9ea94c7002"
            with get_session() as db_session:
                query = select(WifiClient).where(WifiClient.user_fp==user_fp)
                db_client = db_session.scalars(query).first()

            assert None != db_client

    @patch('web.pages.hotspot.authenticate_by_code', return_value={"status": "OK"})
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
    
    @patch('web.pages.hotspot.authenticate_by_code', return_value={"status": "OK"})
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
