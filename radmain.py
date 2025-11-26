import logging
import os

from pyrad2 import dictionary, server

from core.db.session import create_all
from radius.server import HotspotRADIUS


logging.basicConfig(level=logging.DEBUG)

TEST_SERVER = os.environ.get("TEST_RADIUS_SERVER")
TEST_SECRET = os.environ.get("TEST_RADIUS_SECRET")

RADIUS_SERVER = TEST_SERVER
RADIUS_SECRET = TEST_SECRET.encode()


if __name__ == "__main__":
    create_all()
    logging.info("DB loaded")

    srv = HotspotRADIUS(dict=dictionary.Dictionary("radius/dictionary"), coa_enabled=True)
    logging.info("Created server")
    srv.hosts[RADIUS_SERVER] = server.RemoteHost(
        RADIUS_SERVER, RADIUS_SECRET, "cap-test"
    )
    srv.BindToAddress("0.0.0.0")
    logging.info("Start RADIUS server on 0.0.0.0:1812")
    srv.Run()
