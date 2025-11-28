import binascii
import logging

from pyrad2 import server
from pyrad2.constants import PacketType

from core.cache import get_cache
from core.user.repository import check_employee
from core.utils.phone import normalize_phone
from core.wifi.auth import authenticate_by_mac
from core.wifi.challange import radius_check_chap


class HotspotRADIUS(server.Server):
    def HandleAuthPacket(self, pkt):
        logging.info("Received an authentication request")
        logging.debug("Attributes: ")
        for attr in pkt.keys():
            logging.debug(f"{attr}: {pkt[attr]}")

        reply = self.CreateReplyPacket(pkt)
        reply.code = PacketType.AccessReject

        mac = pkt.get("Calling-Station-Id", [""])[0]
        username = pkt.get("User-Name", [""])[0]
        chap_password = pkt.get("CHAP-Password")[0]
        chap_challenge_hex = pkt.get("CHAP-Challenge")[0]
        chap_challenge = binascii.unhexlify(chap_challenge_hex)

        cache = get_cache()

        if username == mac and radius_check_chap(chap_password, chap_challenge, mac):
            client = authenticate_by_mac(mac)
            status = client.get('status')
            if status == "OK":
                is_employee = client.get("employee")
                reply.AddAttribute("MT-Group", "employee" if is_employee else "guest")
                reply.code = PacketType.AccessAccept
        else:
            phone_number = normalize_phone(username)
            token = cache.get(f"auth:token:{phone_number}")
    
            if radius_check_chap(chap_password, chap_challenge, token):
                is_employee = check_employee(phone_number)
                reply.AddAttribute("MT-Group", "employee" if is_employee else "guest")
                reply.code = PacketType.AccessAccept

        reply.add_message_authenticator()
        self.SendReplyPacket(pkt.fd, reply)

    def HandleDisconnectPacket(self, pkt):
        logging.info("Received an disconnect request")
        logging.info("Attributes: ")
        for attr in pkt.keys():
            logging.info(f"{attr}: {pkt[attr]}")

        reply = self.CreateReplyPacket(pkt)
        # COA NAK
        reply.code = 45
        self.SendReplyPacket(pkt.fd, reply)
