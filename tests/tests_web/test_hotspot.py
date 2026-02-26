import unittest
import os
from unittest.mock import patch

from flask import Flask

from core import database
from core.config import get_config, init_config
from core.database.models import Model
from core.database.session import get_session
from core.hotspot.authorization.service import AuthResponse, AuthStatus
from core.hotspot.verification.service import VerificationResponse, VerificationStatus
from core.redis import get_cache
from core.utils.language import get_translate
from web.pages import pages_bp



def _clear_db():
    with get_session() as db_session:
        for table in reversed(Model.metadata.sorted_tables):
            if table.name == 'system_config':
                continue
            db_session.execute(table.delete())
        db_session.commit()


class TestHotspotViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.create_all()
        init_config('web')

    def setUp(self):
        _clear_db()
        self.app = Flask(__name__)
        self.app.debug = True
        self.app.register_blueprint(pages_bp)
        self.app.config['SECRET_KEY'] = 'secret'
        self.app.root_path = os.path.join(os.path.dirname(__file__), '..', '..', 'web')

        @self.app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)

        @self.app.context_processor
        def inject_get_config():
            return dict(get_config=get_config)

        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        with get_cache() as cache:
            cache.clear()
        _clear_db()
        self.ctx.pop()

    @patch('web.pages.hotspot.Authorization.mac_authorization')
    def test_login_failed_renders_page(self, mock_mac_auth):
        mock_mac_auth.return_value = AuthResponse(status=AuthStatus.FAILED, error_message='failed')

        response = self.client.post('/login', data={
            'link-login-only': 'link',
            'link-orig': 'orig',
            'mac': '00:00:00:00:00:01',
            'hardware_fp': 'abc123',
        })
        self.assertEqual(response.status_code, 200)

    @patch('web.pages.hotspot.Authorization.mac_authorization')
    def test_login_authorized_redirects_sendin(self, mock_mac_auth):
        mock_mac_auth.return_value = AuthResponse(
            status=AuthStatus.AUTHORIZED,
            phone='79990000000',
            user_fp='fp',
        )

        response = self.client.post('/login', data={
            'link-login-only': 'link',
            'link-orig': 'orig',
            'mac': '00:00:00:00:00:01',
            'hardware_fp': 'abc123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/sendin', response.location)

    @patch('web.pages.hotspot.Authorization.phone_authorization')
    def test_preauth_blocked(self, mock_phone_auth):
        mock_phone_auth.return_value = AuthResponse(status=AuthStatus.BLOCKED)

        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:01'
                sess['hardware_fp'] = 'fp-hw'

            response = c.post('/preauth', data={'phone': '79990000000'})
            self.assertEqual(response.status_code, 403)

    @patch('web.pages.hotspot.Verification.start_verification')
    @patch('web.pages.hotspot.Authorization.phone_authorization')
    def test_preauth_starts_code_flow(self, mock_phone_auth, mock_start_verification):
        mock_phone_auth.return_value = AuthResponse(status=AuthStatus.FAILED, user_fp='user-fp')
        mock_start_verification.return_value = VerificationResponse(status=VerificationStatus.SENDING_CODE)

        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:01'
                sess['hardware_fp'] = 'fp-hw'

            response = c.post('/preauth', data={'phone': '79990000000'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/code/send', response.location)

    @patch('web.pages.hotspot.Verification.send_code')
    def test_code_send_wait_code(self, mock_send_code):
        mock_send_code.return_value = VerificationResponse(status=VerificationStatus.WAIT_CODE)

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'

            response = c.post('/code/send')
            self.assertEqual(response.status_code, 200)

    @patch('web.pages.hotspot.Verification.code_verification')
    def test_code_auth_denied_redirects_login(self, mock_code_verification):
        mock_code_verification.return_value = VerificationResponse(
            status=VerificationStatus.DENIED,
            error_message='bad code',
        )

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'
                sess['phone'] = '79990000000'
                sess['user_fp'] = 'user-fp'

            response = c.post('/code/auth', data={'code': '0000'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    @patch('web.pages.hotspot.Authorization.authorized', return_value=False)
    def test_sendin_unauthorized(self, _):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['phone'] = '79990000000'
                sess['link-login-only'] = 'http://test/login'
                sess['link-orig'] = 'http://test/orig'
                sess['user_fp'] = 'user-fp'

            response = c.get('/sendin')
            self.assertEqual(response.status_code, 401)
