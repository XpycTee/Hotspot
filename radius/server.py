import socket
from pyrad2 import server, packet
from pyrad2.constants import PacketType

from core.hotspot.user.employees import check_employee
from core.hotspot.user.token import get_token
from core.utils.phone import normalize_phone
from core.hotspot.wifi.auth import authenticate_by_mac
from radius.logging import logger


class HotspotRADIUS(server.Server):
    def _check_password(self, packet: packet.Packet, password: str):
        if 'User-Password' in packet:
            encrypted_user_password = packet.get('User-Password', [''])[0]
            user_password = packet.PwDecrypt(encrypted_user_password)
            auth_success = user_password == password
        elif 'CHAP-Password' in packet:
            auth_success = packet.VerifyChapPasswd(password)
        else:
            auth_success = False
            logger.warning('No password attribute')
        return auth_success

    def _debug_log_attributes(self, packet: packet.Packet):
        logger.debug('Attributes:')
        for attr in packet.keys():
            logger.debug(f'{attr}: {packet[attr]}')

    def _set_accept_reply(self, reply: packet.Packet, is_employee: bool):
        reply.AddAttribute('MT-Group', 'employee' if is_employee else 'guest')
        reply.code = PacketType.AccessAccept

    def HandleAuthPacket(self, packet: packet.Packet):
        logger.info('Received an authentication request')
        self._debug_log_attributes(packet)

        reply = self.CreateReplyPacket(packet)
        reply.code = PacketType.AccessReject

        if packet.verify_message_authenticator():
            mac = packet.get('Calling-Station-Id', [''])[0]
            username = packet.get('User-Name', [''])[0]

            if username == mac:
                if self._check_password(packet, mac):
                    client = authenticate_by_mac(mac)
                    status = client.get('status')
                    if status == 'OK':
                        is_employee = client.get('employee')
                        self._set_accept_reply(reply, is_employee)
                        logger.info('Auth by mac')
                    else:
                        logger.info(f'Auth failed with status: {status}')
                else:
                    logger.info('Auth failed bad token')
            else:
                phone_number = normalize_phone(username)
                token = get_token(phone_number)

                if token and self._check_password(packet, token):
                    is_employee = check_employee(phone_number)
                    self._set_accept_reply(reply, is_employee)
                    logger.info('Auth by token')
                else:
                    logger.info('Auth failed bad token')
        else:
            logger.warning('Bad Message-Authentificator')

        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)

    def HandleAcctPacket(self, packet):
        logger.info('Received an accounting request')
        self._debug_log_attributes(packet)
        reply = self.CreateReplyPacket(packet)
        reply.code = PacketType.AccountingResponse
        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)

    def HandleDisconnectPacket(self, packet):
        logger.info('Received an disconnect request')
        self._debug_log_attributes(packet)

        reply = self.CreateReplyPacket(packet)
        # COA NAK
        reply.code = 45

        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)

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