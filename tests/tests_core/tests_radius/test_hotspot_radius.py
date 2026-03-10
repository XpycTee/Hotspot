import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.hotspot.authorization.service import AuthResponse, AuthStatus
from radius.hotspot import HotspotRADIUS
from pyrad2.constants import PacketType


class TestHotspotRADIUS(unittest.TestCase):
    def setUp(self):
        self.server = HotspotRADIUS.__new__(HotspotRADIUS)
        self.server.logger = MagicMock()
        self.server.reply_accept = MagicMock()
        self.server.reply_reject = MagicMock()
        self.server.send_reply = MagicMock()
        self.server.create_reply_packet = MagicMock()

    def _packet(self):
        packet = MagicMock()
        packet.fd = 10
        return packet

    @patch("radius.hotspot.find_by_mac")
    @patch("radius.hotspot.get_trial_token")
    @patch("radius.hotspot.get_token")
    def test_handle_auth_packet_accepts_token_auth(self, mock_get_token, mock_get_trial_token, mock_find_by_mac):
        packet = self._packet()
        packet.verify_message_authenticator.return_value = True
        packet.get_attribute.side_effect = (
            lambda name: {"Calling-Station-Id": "AA:BB:CC", "User-Name": "AA:BB:CC"}[name]
        )
        packet.verify_password.side_effect = lambda password: password == "token-123"

        accept_reply = MagicMock()
        self.server.reply_accept.return_value = accept_reply
        self.server.reply_reject.return_value = MagicMock()

        mock_get_token.return_value = "token-123"
        mock_get_trial_token.return_value = None
        mock_find_by_mac.return_value = {"is_employee": True}

        self.server.handle_auth_packet(packet)

        self.server.reply_accept.assert_called_once_with(packet, True)
        self.server.send_reply.assert_called_once_with(packet.fd, accept_reply)
        accept_reply.add_message_authenticator.assert_called_once()

    @patch("radius.hotspot.get_trial_token")
    @patch("radius.hotspot.get_token")
    def test_handle_auth_packet_accepts_trial_token(self, mock_get_token, mock_get_trial_token):
        packet = self._packet()
        packet.verify_message_authenticator.return_value = True
        packet.get_attribute.side_effect = (
            lambda name: {"Calling-Station-Id": "AA:BB:CC", "User-Name": "AA:BB:CC"}[name]
        )
        packet.verify_password.side_effect = lambda password: password == "trial-token"

        accept_reply = MagicMock()
        self.server.reply_accept.return_value = accept_reply
        self.server.reply_reject.return_value = MagicMock()
        mock_get_trial_token.return_value = "trial-token"
        mock_get_token.return_value = None

        self.server.handle_auth_packet(packet)

        self.server.reply_accept.assert_called_once_with(packet, group="trial")
        self.server.send_reply.assert_called_once_with(packet.fd, accept_reply)
        accept_reply.add_message_authenticator.assert_called_once()

    @patch("radius.hotspot.Authorization")
    @patch("radius.hotspot.get_trial_token")
    @patch("radius.hotspot.get_token")
    def test_handle_auth_packet_accepts_mac_auth(self, mock_get_token, mock_get_trial_token, mock_authorization_cls):
        packet = self._packet()
        packet.verify_message_authenticator.return_value = True
        packet.get_attribute.side_effect = (
            lambda name: {"Calling-Station-Id": "AA:BB:CC", "User-Name": "user"}[name]
        )
        packet.verify_password.side_effect = lambda password: password == "AA:BB:CC"

        auth_service = MagicMock()
        auth_service.mac_authorization.return_value = AuthResponse(
            status=AuthStatus.AUTHORIZED,
            is_employee=False,
        )
        mock_authorization_cls.return_value = auth_service

        accept_reply = MagicMock()
        self.server.reply_accept.return_value = accept_reply
        self.server.reply_reject.return_value = MagicMock()
        mock_get_token.return_value = None
        mock_get_trial_token.return_value = None

        self.server.handle_auth_packet(packet)

        auth_service.mac_authorization.assert_called_once_with("AA:BB:CC")
        self.server.reply_accept.assert_called_once_with(packet, False)
        self.server.send_reply.assert_called_once_with(packet.fd, accept_reply)
        accept_reply.add_message_authenticator.assert_called_once()

    @patch("radius.hotspot.get_trial_token")
    @patch("radius.hotspot.get_token")
    def test_handle_auth_packet_rejects_bad_token(self, mock_get_token, mock_get_trial_token):
        packet = self._packet()
        packet.verify_message_authenticator.return_value = True
        packet.get_attribute.side_effect = (
            lambda name: {"Calling-Station-Id": "AA:BB:CC", "User-Name": "user"}[name]
        )
        packet.verify_password.return_value = False
        mock_get_token.return_value = "token-123"
        mock_get_trial_token.return_value = None

        initial_reply = MagicMock()
        bad_token_reply = MagicMock()
        self.server.reply_reject.side_effect = [initial_reply, bad_token_reply]

        self.server.handle_auth_packet(packet)

        self.assertEqual(self.server.reply_reject.call_count, 2)
        self.server.reply_reject.assert_any_call(packet, "Bad token")
        self.server.send_reply.assert_called_once_with(packet.fd, bad_token_reply)
        self.server.logger.info.assert_any_call("Bad token")
        bad_token_reply.add_message_authenticator.assert_called_once()

    def test_handle_auth_packet_rejects_bad_message_authenticator(self):
        packet = self._packet()
        packet.verify_message_authenticator.return_value = False

        initial_reply = MagicMock()
        bad_message_reply = MagicMock()
        self.server.reply_reject.side_effect = [initial_reply, bad_message_reply]

        self.server.handle_auth_packet(packet)

        self.assertEqual(self.server.reply_reject.call_count, 2)
        self.server.reply_reject.assert_any_call(packet, "Bad Message-Authentificator")
        self.server.send_reply.assert_called_once_with(packet.fd, bad_message_reply)
        self.server.logger.warning.assert_called_once_with("Bad Message-Authentificator")
        bad_message_reply.add_message_authenticator.assert_called_once()

    def test_handle_acct_packet_updates_statistic_and_sends_accounting_response(self):
        statuses = [("Start", True), ("Alive", True), ("Stop", False), ("Interim", False)]

        for status, expected_alive in statuses:
            with self.subTest(status=status):
                packet = self._packet()
                packet.get_attribute.side_effect = (
                    lambda name, s=status: {
                        "Acct-Status-Type": s,
                        "Calling-Station-Id": "AA:BB:CC",
                        "WISPr-Location-Name": "HQ",
                        "Framed-IP-Address": "10.0.0.1",
                    }[name]
                )
                reply = MagicMock()
                self.server.create_reply_packet.return_value = reply

                with patch("radius.hotspot.update_statistic") as mock_update_statistic:
                    self.server.handle_acct_packet(packet)

                mock_update_statistic.assert_called_once_with(
                    "AA:BB:CC", expected_alive, "HQ", "10.0.0.1"
                )
                self.server.send_reply.assert_called_once_with(packet.fd, reply)
                self.assertEqual(reply.code, PacketType.AccountingResponse)
                reply.add_message_authenticator.assert_called_once()

                self.server.send_reply.reset_mock()
                self.server.create_reply_packet.reset_mock()

    def test_handle_disconnect_packet_sends_coa_nak_and_sets_offline(self):
        packet = self._packet()
        packet.get_attribute.side_effect = (
            lambda name: {
                "Calling-Station-Id": "AA:BB:CC",
                "WISPr-Location-Name": "HQ",
                "Framed-IP-Address": "10.0.0.1",
            }[name]
        )

        reply = MagicMock()
        self.server.create_reply_packet.return_value = reply

        with patch("radius.hotspot.update_statistic") as mock_update_statistic:
            self.server.handle_disconnect_packet(packet)

        mock_update_statistic.assert_called_once_with("AA:BB:CC", False, "HQ", "10.0.0.1")
        self.server.send_reply.assert_called_once_with(packet.fd, reply)
        self.assertEqual(reply.code, 45)
        reply.add_message_authenticator.assert_called_once()

    @patch("radius.hotspot.get_config")
    def test_update_hosts_loads_hosts_from_config(self, mock_get_config):
        hosts = {"127.0.0.1": SimpleNamespace(secret=b"secret")}
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts=hosts))

        self.server.update_hosts()

        self.assertEqual(self.server.hosts, hosts)
