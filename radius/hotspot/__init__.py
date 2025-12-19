from core.hotspot.user.employees import check_employee
from core.hotspot.user.statistic import update_statistic
from core.hotspot.user.token import get_token
from core.hotspot.wifi.auth import authenticate_by_mac
from core.utils.phone import normalize_phone
from radius.logging import logger
from radius.hotspot.packet import BasePacket, HotspotAcctPacket, HotspotAuthPacket
from radius.hotspot.server import BaseServer


from pyrad2.constants import PacketType


class HotspotRADIUS(BaseServer):
    def handle_auth_packet(self, packet: HotspotAuthPacket):
        logger.info('Received an authentication request')
        packet.debug_log_attributes()

        reply = self.reply_reject(packet, 'Bad attributes')

        try:
            verify_packet = packet.verify_message_authenticator()
        except Exception as e:
            reply = self.reply_reject(packet, e, logger.error)

        if verify_packet:
            mac = packet.get_attribute('Calling-Station-Id')
            username = packet.get_attribute('User-Name')

            if username == mac:
                if packet.verify_password(mac):
                    client = authenticate_by_mac(mac)
                    status = client.get('status')
                    if status == 'OK':
                        is_employee = client.get('is_employee')
                        reply = self.reply_accept(packet, is_employee)
                        logger.info('Auth by mac')
                    else:
                        reply = self.reply_reject(packet, f'Auth failed with status: {status}')
                else:
                    reply = self.reply_reject(packet, 'Auth failed bad token')
            else:
                phone_number = normalize_phone(username)
                token = get_token(phone_number)
                non_token = get_token(phone_number)

                if token and packet.verify_password(token):
                    is_employee = check_employee(phone_number)
                    reply = self.reply_accept(packet, is_employee)
                    logger.info('Auth by token')
                else:
                    reply = self.reply_reject(packet, 'Auth failed bad token')
        else:
            reply = self.reply_reject(packet, 'Bad Message-Authentificator', logger.warning)

        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)

    def handle_acct_packet(self, packet: HotspotAcctPacket):
        #logger.info('Received an accounting request')
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

        reply = packet.create_reply()
        reply.code = PacketType.AccountingResponse
        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)

    def handle_disconnect_packet(self, packet: BasePacket):
        logger.info('Received an disconnect request')
        packet.debug_log_attributes()

        alive = False
        mac = packet.get_attribute('Calling-Station-Id')
        location = packet.get_attribute('WISPr-Location-Name')
        ip_address = packet.get_attribute('Framed-IP-Address')

        update_statistic(mac, alive, location, ip_address)

        reply = packet.create_reply()
        # COA NAK
        reply.code = 45

        reply.add_message_authenticator()
        self.send_reply(packet.fd, reply)