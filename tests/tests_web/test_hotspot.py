import unittest
import os
from unittest.mock import patch
import json

from flask import Flask

from core import database
from core.config import get_config, init_config
from core.database.models import Model
from core.database.session import get_session
from core.hotspot.authorization.service import AuthResponse, AuthStatus, AuthFailReason
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
    def test_login_not_found_renders_page_without_error(self, mock_mac_auth):
        mock_mac_auth.return_value = AuthResponse(
            status=AuthStatus.FAILED,
            error_message='User not found',
            fail_reason=AuthFailReason.NOT_FOUND,
        )

        response = self.client.post('/login', data={
            'link-login-only': 'link',
            'link-orig': 'orig',
            'mac': '00:00:00:00:00:01',
            'hardware_fp': 'abc123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('User not found', response.get_data(as_text=True))

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

    @patch('web.pages.hotspot.Authorization.authorization')
    @patch('web.pages.hotspot.Verification.code_verification')
    def test_code_auth_verified_but_auth_failed_redirects_login(self, mock_code_verification, mock_authorization):
        mock_code_verification.return_value = VerificationResponse(status=VerificationStatus.VERIFIED)
        mock_authorization.return_value = AuthResponse(
            status=AuthStatus.FAILED,
            error_message='auth failed',
        )

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'
                sess['mac'] = '00:00:00:00:00:01'
                sess['phone'] = '79990000000'
                sess['hardware_fp'] = 'fp-hw'

            response = c.post('/code/auth', data={'code': '0000'})
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)
            mock_authorization.assert_called_once_with('00:00:00:00:00:01', '79990000000', 'fp-hw')

            with c.session_transaction() as sess:
                self.assertEqual(sess.get('error'), 'auth failed')
                self.assertIsNone(sess.get('phone'))
                self.assertIsNone(sess.get('verify_session_id'))

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

    @patch('web.pages.hotspot.Verification.call_verification')
    def test_call_check_stream_verified(self, mock_call_verification):
        mock_call_verification.return_value = VerificationResponse(status=VerificationStatus.VERIFIED)

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'

            response = c.get('/call/check/stream')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/event-stream')

            body = response.data.decode('utf-8')
            events = [line for line in body.splitlines() if line.startswith('data: ')]
            self.assertTrue(events)

            payload = json.loads(events[-1].replace('data: ', '', 1))
            self.assertEqual(payload.get('state'), 'verified')

    @patch('web.pages.hotspot.Authorization.authorization')
    def test_call_auth_failed_redirects_login(self, mock_authorization):
        mock_authorization.return_value = AuthResponse(
            status=AuthStatus.FAILED,
            error_message='auth failed',
        )

        with self.client as c:
            with c.session_transaction() as sess:
                sess['mac'] = '00:00:00:00:00:01'
                sess['phone'] = '79990000000'
                sess['hardware_fp'] = 'fp-hw'
                sess['verify_session_id'] = 'verify-session'

            response = c.get('/call/auth')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)
            mock_authorization.assert_called_once_with('00:00:00:00:00:01', '79990000000', 'fp-hw')

            with c.session_transaction() as sess:
                self.assertEqual(sess.get('error'), 'auth failed')
                self.assertIsNone(sess.get('phone'))
                self.assertIsNone(sess.get('verify_session_id'))

    @patch('web.pages.hotspot.Verification.call_verification')
    def test_call_check_stream_timeout(self, mock_call_verification):
        mock_call_verification.return_value = VerificationResponse(
            status=VerificationStatus.TIMEOUT,
            error_message='call expired',
        )

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'

            response = c.get('/call/check/stream')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/event-stream')

            body = response.data.decode('utf-8')
            events = [line for line in body.splitlines() if line.startswith('data: ')]
            self.assertTrue(events)

            payload = json.loads(events[-1].replace('data: ', '', 1))
            self.assertEqual(payload.get('state'), 'timeout')
            self.assertEqual(payload.get('message'), 'call expired')

    @patch('web.pages.hotspot.Verification.call_verification')
    def test_call_check_stream_error(self, mock_call_verification):
        mock_call_verification.return_value = VerificationResponse(
            status=VerificationStatus.ERROR,
            error_message='provider failed',
        )

        with self.client as c:
            with c.session_transaction() as sess:
                sess['verify_session_id'] = 'verify-session'

            response = c.get('/call/check/stream')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/event-stream')

            body = response.data.decode('utf-8')
            events = [line for line in body.splitlines() if line.startswith('data: ')]
            self.assertTrue(events)

            payload = json.loads(events[-1].replace('data: ', '', 1))
            self.assertEqual(payload.get('state'), 'failed')
            self.assertEqual(payload.get('message'), 'provider failed')
