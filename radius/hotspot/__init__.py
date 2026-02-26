from core.config import get_config
from core.hotspot.authorization.service import AuthStatus, Authorization
from core.hotspot.user.employees import check_employee
from core.hotspot.user.statistic import update_statistic
from core.hotspot.user.token import get_token
from core.logging import get_logger
from core.utils.phone import normalize_phone
from radius.hotspot.packet import BasePacket, HotspotAcctPacket, HotspotAuthPacket
from radius.hotspot.server import BaseServer


from pyrad2.constants import PacketType


class HotspotRADIUS(BaseServer):
    def __init__(self, addresses=None, authport=1812, acctport=1813, coaport=3799, hosts=None, dict=None, auth_enabled=True, acct_enabled=True, coa_enabled=False, worker_id=0):
        super().__init__(addresses, authport, acctport, coaport, hosts, dict, auth_enabled, acct_enabled, coa_enabled)
        self.logger = get_logger(f'RADIUS #{worker_id} server')

    def update_hosts(self):
        self.hosts = get_config().radius.hosts

    def handle_auth_packet(self, packet: HotspotAuthPacket):
        self.logger.info('Received an authentication request')
        packet.debug_log_attributes()

        log_ = self.logger.info

        reply_message = 'Bad attributes'
        reply = self.reply_reject(packet, reply_message)

        try:
            verify_packet = packet.verify_message_authenticator()
        except Exception as e:
            reply = self.reply_reject(packet, e)
            self.logger.error(e)

        if verify_packet:
            mac = packet.get_attribute('Calling-Station-Id')
            username = packet.get_attribute('User-Name')

            if username == mac:
                if packet.verify_password(mac):
                    auth_service = Authorization()
                    client = auth_service.mac_authorization(mac, None)
                    if client.status == AuthStatus.AUTHORIZED:
                        is_employee = client.is_employee
                        reply = self.reply_accept(packet, is_employee)
                        reply_message = 'Auth by mac'
                    else:
                        reply = self.reply_reject(packet, client.error_message)
                else:
                    reply_message =  'Bad token'
                    reply = self.reply_reject(packet ,reply_message)
            else:
                phone_number = normalize_phone(username)
                token = get_token(phone_number)

                if token and packet.verify_password(token):
                    is_employee = check_employee(phone_number)
                    reply = self.reply_accept(packet, is_employee)
                    reply_message = 'Auth by token'
                else:
                    reply_message = 'Bad token'
                    reply = self.reply_reject(packet, reply_message)
        else:
            reply_message = 'Bad Message-Authentificator'
            reply = self.reply_reject(packet, reply_message)
            log_ = self.logger.warning

        log_(reply_message)
        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)

    def handle_acct_packet(self, packet: HotspotAcctPacket):
        #self.logger.info('Received an accounting request')
        #packet.debug_log_attributes()

        alive = False
        status_type = packet.get_attribute('Acct-Status-Type')
        mac = packet.get_attribute('Calling-Station-Id')
        location = packet.get_attribute('WISPr-Location-Name')
        ip_address = packet.get_attribute('Framed-IP-Address')

        if status_type in ['Start', 'Alive']:
            alive = True
        elif status_type == 'Stop':
            alive = False

        update_statistic(mac, alive, location, ip_address)

        reply = self.create_reply_packet(packet)
        reply.code = PacketType.AccountingResponse
        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)

    def handle_disconnect_packet(self, packet: BasePacket):
        self.logger.info('Received an disconnect request')
        packet.debug_log_attributes()

        alive = False
        mac = packet.get_attribute('Calling-Station-Id')
        location = packet.get_attribute('WISPr-Location-Name')
        ip_address = packet.get_attribute('Framed-IP-Address')

        update_statistic(mac, alive, location, ip_address)

        reply = self.create_reply_packet(packet)
        # COA NAK
        reply.code = 45

        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)