import hashlib
import time
import unittest
from unittest.mock import patch

from flask import Flask

from core.redis import get_cache
from web.webhooks import webhooks_bp


def _build_hash(api_key: str, entries: list[str]) -> str:
    return hashlib.sha256((api_key + "".join(entries)).encode("utf-8")).hexdigest()


def _build_callcheck_entry(check_id: str, check_status: int) -> str:
    return f"callcheck_status\n{check_id}\n{check_status}\n{time.time()}"


class TestSmsruWebhook(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(webhooks_bp)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.api_key = "test-api-key"

    def tearDown(self):
        with get_cache() as cache:
            cache.clear()
        self.app_context.pop()

    @patch('web.webhooks.smsru._get_smsru_api_key')
    def test_hash_missing(self, mock_api_key):
        mock_api_key.return_value = self.api_key

        entry = _build_callcheck_entry("check-1", 401)
        response = self.client.post('/webhook/smsru', data={
            'data[0]': entry,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_data(as_text=True), "hash missing")

    @patch('web.webhooks.smsru._get_smsru_api_key')
    def test_invalid_hash(self, mock_api_key):
        mock_api_key.return_value = self.api_key

        entry = _build_callcheck_entry("check-1", 401)
        response = self.client.post('/webhook/smsru', data={
            'data[0]': entry,
            'hash': 'invalid',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_data(as_text=True), "100")

    @patch('web.webhooks.smsru._get_smsru_api_key')
    def test_cache_miss_does_not_fail(self, mock_api_key):
        mock_api_key.return_value = self.api_key

        entry = _build_callcheck_entry("check-miss", 401)
        payload = {'data[0]': entry}
        payload['hash'] = _build_hash(self.api_key, [entry])

        response = self.client.post('/webhook/smsru', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "100")

    @patch('web.webhooks.smsru.finalize_verified_trial')
    @patch('web.webhooks.smsru._get_smsru_api_key')
    def test_verified_status_triggers_trial_finalize(self, mock_api_key, mock_finalize):
        mock_api_key.return_value = self.api_key
        check_id = "check-finalize"
        with get_cache() as cache:
            cache.set(f'callcheck:smsru:id:{check_id}', {'confirm': {'check_status': 400}}, 600)

        entry = _build_callcheck_entry(check_id, 401)
        payload = {'data[0]': entry}
        payload['hash'] = _build_hash(self.api_key, [entry])

        response = self.client.post('/webhook/smsru', data=payload)
        self.assertEqual(response.status_code, 200)
        mock_finalize.assert_called_once_with('smsru', check_id)

    @patch('web.webhooks.smsru._get_smsru_api_key')
    def test_replay_is_ignored(self, mock_api_key):
        mock_api_key.return_value = self.api_key
        check_id = "check-replay"

        with get_cache() as cache:
            cache.set(f'callcheck:smsru:id:{check_id}', {'confirm': {'check_status': 400}}, 600)

        entry = _build_callcheck_entry(check_id, 401)
        payload = {'data[0]': entry}
        payload['hash'] = _build_hash(self.api_key, [entry])

        first = self.client.post('/webhook/smsru', data=payload)
        self.assertEqual(first.status_code, 200)

        with get_cache() as cache:
            data = cache.get(f'callcheck:smsru:id:{check_id}')
            self.assertEqual(data['confirm']['check_status'], 401)
            data['confirm']['check_status'] = 400
            cache.set(f'callcheck:smsru:id:{check_id}', data, 600)

        second = self.client.post('/webhook/smsru', data=payload)
        self.assertEqual(second.status_code, 200)

        with get_cache() as cache:
            data = cache.get(f'callcheck:smsru:id:{check_id}')
            self.assertEqual(data['confirm']['check_status'], 400)
