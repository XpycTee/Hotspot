import logging

from pyrad2 import server
from pyrad2.constants import PacketType

from core.cache import get_cache
from core.user.token import token_to_urlsafe
from core.wifi.auth import authenticate_by_mac, authenticate_by_phone
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
        cache = get_cache()

        if username == mac and radius_check_chap(pkt, mac):
            client = authenticate_by_mac(mac)
            status = client.get('status')
            if status == "OK":
                employee = client.get("employee")
                reply.AddAttribute("MT-Group", "employee" if employee else "guest")
                reply.code = PacketType.AccessAccept
        else:
            raw_token = cache.get(f"{mac}:{username}:token")
            if radius_check_chap(pkt, token_to_urlsafe(raw_token)):
                client = authenticate_by_phone(mac, username)
                status = client.get('status')
                if status == "OK":
                    employee = client.get("employee")
                    reply.AddAttribute("MT-Group", "employee" if employee else "guest")
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

