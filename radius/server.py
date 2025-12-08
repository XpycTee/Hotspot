import socket
from pyrad2 import server, packet
from pyrad2.constants import PacketType

from core.hotspot.user.employees import check_employee
from core.hotspot.user.statistic import update_statistic
from core.hotspot.user.token import get_token
from core.utils.phone import normalize_phone
from core.hotspot.wifi.auth import authenticate_by_mac
from radius.logging import logger

class BasePacket(packet.Packet):
    def debug_log_attributes(self):
        logger.debug('Attributes:')
        for attr in self.keys():
            logger.debug(f'{attr}: {self[attr]}')

    def get_attribute(self, key, default=None):
        return self.get(key, [default])[0]


class HotspotAuthPacket(BasePacket, packet.AuthPacket):
    def verify_password(self, password: str):
        if 'User-Password' in self:
            encrypted_user_password = self.get_attribute('User-Password')
            user_password = self.PwDecrypt(encrypted_user_password)
            auth_success = user_password == password
        elif 'CHAP-Password' in self:
            auth_success = self.VerifyChapPasswd(password)
        else:
            auth_success = False
            logger.warning('No password attribute')
        return auth_success


class HotspotAcctPacket(BasePacket, packet.AcctPacket):
    pass


class BaseServer(server.Server):
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


class HotspotRADIUS(BaseServer):
    @staticmethod
    def _set_accept_reply(reply: packet.Packet, is_employee: bool):
        reply.AddAttribute('MT-Group', 'employee' if is_employee else 'guest')
        reply.code = PacketType.AccessAccept

    def HandleAuthPacket(self, packet: HotspotAuthPacket):
        logger.info('Received an authentication request')
        packet.debug_log_attributes()

        reply = self.CreateReplyPacket(packet)
        reply.code = PacketType.AccessReject

        if packet.verify_message_authenticator():
            mac = packet.get_attribute('Calling-Station-Id')
            username = packet.get_attribute('User-Name')

            if username == mac:
                if packet.verify_password(mac):
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

                if token and packet.verify_password(token):
                    is_employee = check_employee(phone_number)
                    self._set_accept_reply(reply, is_employee)
                    logger.info('Auth by token')
                else:
                    logger.info('Auth failed bad token')
        else:
            logger.warning('Bad Message-Authentificator')

        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)

    def HandleAcctPacket(self, packet: HotspotAcctPacket):
        logger.info('Received an accounting request')
        packet.debug_log_attributes()

        status = False
        status_type = packet.get_attribute('Acct-Status-Type')
        mac = packet.get_attribute('Calling-Station-Id')
        location = packet.get_attribute('WISPr-Location-Name')
        ip_address = packet.get_attribute('Framed-IP-Address')

        if status_type in ['Start', 'Alive']:
            status = True
        elif status_type == 'Stop':
            status = False

        update_statistic(mac, status, location, ip_address)

        reply = self.CreateReplyPacket(packet)
        reply.code = PacketType.AccountingResponse
        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)

    def HandleDisconnectPacket(self, packet):
        logger.info('Received an disconnect request')
        packet.debug_log_attributes()

        reply = self.CreateReplyPacket(packet)
        # COA NAK
        reply.code = 45

        reply.add_message_authenticator()
        self.SendReplyPacket(packet.fd, reply)
