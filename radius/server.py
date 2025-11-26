import binascii
import hashlib
import logging

from pyrad2 import server
from pyrad2.constants import PacketType

from core.wifi.auth import authenticate_by_mac

def check_chap(request, stored_password):
    # stored_password — твой "чистый" пароль, который должен знать сервер
    # request — это AccessRequest из pyrad2

    chap_password = request.get("CHAP-Password")[0]
    chap_challenge_hex = request.get("CHAP-Challenge")[0]
    chap_challenge = binascii.unhexlify(chap_challenge_hex)
    
    # 1. Извлекаем ID
    chap_id = chap_password[0]

    # 2. Извлекаем хеш
    received_hash = chap_password[1:]   # 16 байт

    # 3. Делаем наш хеш
    m = hashlib.md5()
    m.update(bytes([chap_id]))
    m.update(stored_password.encode("utf-8"))
    m.update(chap_challenge)
    expected_hash = m.digest()

    return received_hash == expected_hash

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

        if username == mac and check_chap(pkt, mac):
            client = authenticate_by_mac(mac)
            status = client.get('status')
            if status == "OK":
                employee = client.get("employee")
                reply.AddAttribute("MT-Group", "employee" if employee else "guest")
                reply.code = PacketType.AccessAccept
        else:
            if check_chap(pkt, "qwerty"):
                print("NT")
            else:
                print("Bad PASSW")

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

