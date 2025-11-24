import logging
import os
from pyrad2 import dictionary, server
from pyrad2.constants import PacketType

logging.basicConfig(level=logging.INFO)

TEST_SERVER = os.environ.get("TEST_RADIUS_SERVER")
TEST_SECRET = os.environ.get("TEST_RADIUS_SECRET")

RADIUS_SERVER = TEST_SERVER
RADIUS_SECRET = TEST_SECRET.encode()


def auth_by_mac(mac, reply):
    logging.debug(f"Find {mac} in db")
    test_db = {"00:00:00:00:00:00": {"employee": True} }
    employee = test_db.get("employee", False)
    reply.AddAttribute("MT-Group", "employee" if employee else "guest")
    reply.code = PacketType.AccessAccept


class TESTRADIUS(server.Server):
    def HandleAuthPacket(self, pkt):
        logging.info("Received an authentication request")
        logging.debug("Attributes: ")
        for attr in pkt.keys():
            logging.debug(f"{attr}: {pkt[attr]}")

        reply = self.CreateReplyPacket(pkt)
        reply.code = PacketType.AccessReject

        mac = pkt.get("User-Name", [""])[0]
        if not mac:
            mac = pkt.get("Calling-Station-Id", [""])[0]

        if mac:
            auth_by_mac(mac, reply)
            
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


if __name__ == "__main__":
    srv = TESTRADIUS(dict=dictionary.Dictionary("dictionary"), coa_enabled=True)

    srv.hosts[RADIUS_SERVER] = server.RemoteHost(
        RADIUS_SERVER, RADIUS_SECRET, "cap-test"
    )
    srv.BindToAddress("0.0.0.0")

    srv.Run()
