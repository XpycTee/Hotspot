import unittest
from unittest.mock import patch

from flask import Flask

from core.redis import get_cache
from web.webhooks import webhooks_bp


class TestAsteriskWebhook(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(webhooks_bp)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.api_key = "asterisk-api-key"

    def tearDown(self):
        with get_cache() as cache:
            cache.clear()
        self.app_context.pop()

    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_fail_closed_when_provider_key_missing(self, mock_expected_key):
        mock_expected_key.return_value = None
        response = self.client.post('/webhook/asterisk', data={
            'api_key': self.api_key,
            'phone': '79990000000',
        })
        self.assertEqual(response.status_code, 503)

    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_bad_api_key(self, mock_expected_key):
        mock_expected_key.return_value = self.api_key
        response = self.client.post('/webhook/asterisk', data={
            'api_key': 'wrong',
            'phone': '79990000000',
        })
        self.assertEqual(response.status_code, 403)

    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_post_header_token_updates_status(self, mock_expected_key):
        mock_expected_key.return_value = self.api_key

        with get_cache() as cache:
            cache.set('callcheck:asterisk:phone:79990000000', 'req-1', 300)
            cache.set('callcheck:asterisk:id:req-1', {'status': False, 'phone': '79990000000'}, 300)

        response = self.client.post(
            '/webhook/asterisk',
            json={'phone': '+7 (999) 000-00-00'},
            headers={'X-Webhook-Token': self.api_key},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), 'OK')

        with get_cache() as cache:
            data = cache.get('callcheck:asterisk:id:req-1')
            self.assertTrue(data['status'])

    @patch('web.webhooks.asterisk.finalize_verified_trial')
    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_post_header_token_triggers_trial_finalize(self, mock_expected_key, mock_finalize):
        mock_expected_key.return_value = self.api_key
        with get_cache() as cache:
            cache.set('callcheck:asterisk:phone:79990000003', 'req-4', 300)
            cache.set('callcheck:asterisk:id:req-4', {'status': False, 'phone': '79990000003'}, 300)

        response = self.client.post(
            '/webhook/asterisk',
            json={'phone': '+7 (999) 000-00-03'},
            headers={'X-Webhook-Token': self.api_key},
        )
        self.assertEqual(response.status_code, 200)
        mock_finalize.assert_called_once_with('asterisk', 'req-4')

    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_get_compatibility(self, mock_expected_key):
        mock_expected_key.return_value = self.api_key

        with get_cache() as cache:
            cache.set('callcheck:asterisk:phone:79990000001', 'req-2', 300)
            cache.set('callcheck:asterisk:id:req-2', {'status': False, 'phone': '79990000001'}, 300)

        response = self.client.get(
            '/webhook/asterisk',
            query_string={'api_key': self.api_key, 'phone': '79990000001'},
        )
        self.assertEqual(response.status_code, 200)

    @patch('web.webhooks.asterisk._get_expected_api_key')
    def test_replay_event_id_is_ignored(self, mock_expected_key):
        mock_expected_key.return_value = self.api_key

        with get_cache() as cache:
            cache.set('callcheck:asterisk:phone:79990000002', 'req-3', 300)
            cache.set('callcheck:asterisk:id:req-3', {'status': False, 'phone': '79990000002'}, 300)

        first = self.client.post('/webhook/asterisk', data={
            'api_key': self.api_key,
            'phone': '79990000002',
            'event_id': 'event-1',
        })
        self.assertEqual(first.status_code, 200)

        with get_cache() as cache:
            data = cache.get('callcheck:asterisk:id:req-3')
            self.assertTrue(data['status'])
            data['status'] = False
            cache.set('callcheck:asterisk:id:req-3', data, 300)

        second = self.client.post('/webhook/asterisk', data={
            'api_key': self.api_key,
            'phone': '79990000002',
            'event_id': 'event-1',
        })
        self.assertEqual(second.status_code, 200)

        with get_cache() as cache:
            data = cache.get('callcheck:asterisk:id:req-3')
            self.assertFalse(data['status'])
