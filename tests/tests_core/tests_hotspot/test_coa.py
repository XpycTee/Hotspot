import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pyrad2.constants import PacketType

from core.hotspot.wifi.coa import send_group_switch


class TestCoASender(unittest.TestCase):
    @patch('core.hotspot.wifi.coa.dictionary.Dictionary')
    @patch('core.hotspot.wifi.coa.client.Client')
    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_ack(self, mock_get_config, mock_find_session_attrs_by_mac, mock_client_cls, _):
        host = SimpleNamespace(
            address='10.0.0.1',
            secret=b'secret',
            authport=1812,
            acctport=1813,
            coaport=3799,
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.1': host}))
        mock_find_session_attrs_by_mac.return_value = None

        mock_client = MagicMock()
        packet = MagicMock()
        mock_client.CreateCoAPacket.return_value = packet
        mock_client.SendPacket.return_value = SimpleNamespace(code=PacketType.CoAACK)
        mock_client_cls.return_value = mock_client

        result = send_group_switch(
            mac='AA:BB:CC:00:00:01',
            target_group='guest',
            nas_target={'nas_ip': '10.0.0.1'},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.code, PacketType.CoAACK)
        packet.AddAttribute.assert_any_call('Calling-Station-Id', 'AA:BB:CC:00:00:01')
        packet.AddAttribute.assert_any_call('User-Name', 'AA:BB:CC:00:00:01')
        packet.AddAttribute.assert_any_call('MT-Group', 'guest')

    @patch('core.hotspot.wifi.coa.dictionary.Dictionary')
    @patch('core.hotspot.wifi.coa.client.Client')
    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_nak(self, mock_get_config, mock_find_session_attrs_by_mac, mock_client_cls, _):
        host = SimpleNamespace(
            address='10.0.0.2',
            secret=b'secret',
            authport=1812,
            acctport=1813,
            coaport=3799,
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.2': host}))
        mock_find_session_attrs_by_mac.return_value = None

        mock_client = MagicMock()
        mock_client.CreateCoAPacket.return_value = MagicMock()
        mock_client.SendPacket.side_effect = [
            SimpleNamespace(code=PacketType.CoANAK),
            SimpleNamespace(code=PacketType.DisconnectACK),
        ]
        mock_client_cls.return_value = mock_client

        result = send_group_switch(
            mac='AA:BB:CC:00:00:02',
            target_group='employee',
            nas_target={'radius_client_ip': '10.0.0.2'},
        )
        self.assertTrue(result.success)
        self.assertEqual(result.operation, 'disconnect_fallback')
        self.assertEqual(result.code, PacketType.DisconnectACK)

    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_host_not_found(self, mock_get_config, mock_find_session_attrs_by_mac):
        host = SimpleNamespace(
            address='10.0.0.3',
            secret=b'secret',
            authport=1812,
            acctport=1813,
            coaport=3799,
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.3': host}))
        mock_find_session_attrs_by_mac.return_value = None

        result = send_group_switch(
            mac='AA:BB:CC:00:00:03',
            target_group='guest',
            nas_target={'nas_ip': '10.0.0.99'},
        )
        self.assertFalse(result.success)

    @patch('core.hotspot.wifi.coa.dictionary.Dictionary')
    @patch('core.hotspot.wifi.coa.client.Client')
    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_disconnect_fallback_fail(self, mock_get_config, mock_find_session_attrs_by_mac, mock_client_cls, _):
        host = SimpleNamespace(
            address='10.0.0.4',
            secret=b'secret',
            authport=1812,
            acctport=1813,
            coaport=3799,
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.4': host}))
        mock_find_session_attrs_by_mac.return_value = None

        mock_client = MagicMock()
        mock_client.CreateCoAPacket.return_value = MagicMock()
        mock_client.SendPacket.side_effect = [
            SimpleNamespace(code=PacketType.CoANAK),
            SimpleNamespace(code=PacketType.DisconnectNAK),
        ]
        mock_client_cls.return_value = mock_client

        result = send_group_switch(
            mac='AA:BB:CC:00:00:04',
            target_group='guest',
            nas_target={'nas_ip': '10.0.0.4'},
        )
        self.assertFalse(result.success)
        self.assertEqual(result.operation, 'disconnect_fallback')
        self.assertEqual(result.code, PacketType.DisconnectNAK)

    @patch('core.hotspot.wifi.coa.dictionary.Dictionary')
    @patch('core.hotspot.wifi.coa.client.Client')
    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_accepts_string_ports(self, mock_get_config, mock_find_session_attrs_by_mac, mock_client_cls, _):
        host = SimpleNamespace(
            address='10.0.0.5',
            secret=b'secret',
            authport='1812',
            acctport='1813',
            coaport='3799',
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.5': host}))
        mock_find_session_attrs_by_mac.return_value = None

        mock_client = MagicMock()
        packet = MagicMock()
        mock_client.CreateCoAPacket.return_value = packet
        mock_client.SendPacket.return_value = SimpleNamespace(code=PacketType.CoAACK)
        mock_client_cls.return_value = mock_client

        result = send_group_switch(
            mac='AA:BB:CC:00:00:05',
            target_group='guest',
            nas_target={'nas_ip': '10.0.0.5'},
        )

        self.assertTrue(result.success)
        self.assertEqual(result.code, PacketType.CoAACK)
        _, kwargs = mock_client_cls.call_args
        self.assertEqual(kwargs['authport'], 1812)
        self.assertEqual(kwargs['acctport'], 1813)
        self.assertEqual(kwargs['coaport'], 3799)

    @patch('core.hotspot.wifi.coa.dictionary.Dictionary')
    @patch('core.hotspot.wifi.coa.client.Client')
    @patch('core.hotspot.wifi.coa.find_session_attrs_by_mac')
    @patch('core.hotspot.wifi.coa.get_config')
    def test_send_group_switch_adds_framed_ip_if_present(self, mock_get_config, mock_find_session_attrs_by_mac, mock_client_cls, _):
        host = SimpleNamespace(
            address='10.0.0.10',
            secret=b'secret',
            authport=1812,
            acctport=1813,
            coaport=3799,
            enabled=True,
        )
        mock_get_config.return_value = SimpleNamespace(radius=SimpleNamespace(hosts={'10.0.0.10': host}))
        mock_find_session_attrs_by_mac.return_value = {'last_ipv4_address': '10.10.10.50', 'last_location': 'HQ'}

        mock_client = MagicMock()
        packet = MagicMock()
        mock_client.CreateCoAPacket.return_value = packet
        mock_client.SendPacket.return_value = SimpleNamespace(code=PacketType.CoAACK)
        mock_client_cls.return_value = mock_client

        result = send_group_switch(
            mac='AA:BB:CC:00:00:10',
            target_group='guest',
            nas_target={'nas_ip': '10.0.0.10'},
        )

        self.assertTrue(result.success)
        packet.AddAttribute.assert_any_call('Framed-IP-Address', '10.10.10.50')
