import ipaddress
import socket

from pyrad2 import server, packet
from pyrad2.exceptions import ServerPacketError
from pyrad2.constants import PacketType

from core.logging import get_logger
from radius.hotspot.packet import HotspotAcctPacket, HotspotAuthPacket


logger = get_logger('radius.hotpsot.server')

class BaseServer(server.Server):
    def __init__(self, addresses = None, authport = 1812, acctport = 1813, coaport = 3799, hosts = None, dict = None, auth_enabled = True, acct_enabled = True, coa_enabled = False):
        super().__init__(addresses, authport, acctport, coaport, hosts, dict, auth_enabled, acct_enabled, coa_enabled)

    @staticmethod
    def _unmapped_ip(ip: str) -> str:
        addr = ipaddress.ip_address(ip)

        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            return str(addr.ipv4_mapped)

        return str(addr)

    def reply_accept(self, packet, is_employee):
        reply = self.create_reply_packet(packet)
        reply.AddAttribute('MT-Group', 'employee' if is_employee else 'guest')
        reply.code = PacketType.AccessAccept
        return reply

    def reply_reject(self, packet, error_message: str):
        reply = self.create_reply_packet(packet)
        reply.AddAttribute('Reply-Message', error_message)
        reply.code = PacketType.AccessReject
        return reply

    def send_reply(self, fd, pkt):
        return super().SendReplyPacket(fd, pkt)

    def handle_auth_packet(self, pkt):
        """Authentication packet handler.
        This is an empty function that is called when a valid
        authentication packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        Args:
            pkt (packet.Packet): Packet to process
        """
        pass
    
    def handle_acct_packet(self, pkt):
        """Accounting packet handler.
        This is an empty function that is called when a valid
        accounting packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        Args:
            pkt (packet.Packet): Packet to process
        """
        pass
    
    def handle_coa_packet(self, pkt):
        """CoA packet handler.
        This is an empty function that is called when a valid
        accounting packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        Args:
            pkt (packet.Packet): Packet to process
        """
        pass
    
    def handle_disconnect_packet(self, pkt):
        """CoA packet handler.
        This is an empty function that is called when a valid
        accounting packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        Args:
            pkt (packet.Packet): Packet to process
        """
        pass

    def _HandleAuthPacket(self, pkt: packet.Packet) -> None:
        """Process a packet received on the authentication port.
        If this packet should be dropped instead of processed a
        ServerPacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        Args:
            pkt (packet.Packet): Packet to process
        """
        self._AddSecret(pkt)
        if pkt.code != PacketType.AccessRequest:
            raise ServerPacketError(
                "Received non-authentication packet on authentication port"
            )
        self.handle_auth_packet(pkt)

    def _HandleAcctPacket(self, pkt: packet.Packet) -> None:
        """Process a packet received on the accounting port.
        If this packet should be dropped instead of processed a
        ServerPacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        Args:
            pkt (packet.Packet): Packet to process
        """
        self._AddSecret(pkt)
        if pkt.code not in [
            PacketType.AccountingRequest,
            PacketType.AccountingResponse,
        ]:
            raise ServerPacketError("Received non-accounting packet on accounting port")
        self.handle_acct_packet(pkt)

    def _HandleCoaPacket(self, pkt: packet.Packet) -> None:
        """Process a packet received on the coa port.
        If this packet should be dropped instead of processed a
        ServerPacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        Args:
            pkt (packet.Packet): Packet to process
        """
        self._AddSecret(pkt)
        if pkt.code == PacketType.CoARequest:
            self.handle_coa_packet(pkt)
        elif pkt.code == PacketType.DisconnectRequest:
            self.handle_disconnect_packet(pkt)
        else:
            raise ServerPacketError("Received non-coa packet on coa port")

    def _AddSecret(self, pkt: packet.Packet) -> None:
        host_address = self._unmapped_ip(pkt.source[0])
        if host_address in self.hosts:
            pkt.secret = self.hosts[host_address].secret
        elif "0.0.0.0" in self.hosts:
            pkt.secret = self.hosts["0.0.0.0"].secret
        else:
            raise ServerPacketError("Received packet from unknown host")
    
    def BindToAddress(self, addr: str) -> None:
        addrFamily = self._GetAddrInfo(addr)
        for family, address in addrFamily:
            if self.auth_enabled:
                authfd = socket.socket(family, socket.SOCK_DGRAM)
                authfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                authfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                authfd.bind((address, self.authport))
                self.authfds.append(authfd)

            if self.acct_enabled:
                acctfd = socket.socket(family, socket.SOCK_DGRAM)
                acctfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                acctfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                acctfd.bind((address, self.acctport))
                self.acctfds.append(acctfd)

            if self.coa_enabled:
                coafd = socket.socket(family, socket.SOCK_DGRAM)
                coafd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                coafd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                coafd.bind((address, self.coaport))
                self.coafds.append(coafd)

    def CreateAuthPacket(self, **args) -> packet.Packet:
        return HotspotAuthPacket(dict=self.dict, **args)

    def CreateAcctPacket(self, **args) -> packet.Packet:
        return HotspotAcctPacket(dict=self.dict, **args)

    def create_reply_packet(self, pkt, **attributes):
        return super().CreateReplyPacket(pkt, **attributes)