import logging

from pyrad2 import dictionary, server

from core import database
from core.config.radius import RADIUS_HOST, RADIUS_PORT, RADIUS_SECRET, RADIUS_CLIENT
from radius.server import HotspotRADIUS


logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    database.create_all()
    logging.info("DB loaded")

    srv = HotspotRADIUS(dict=dictionary.Dictionary("radius/dictionary"), coa_enabled=True)
    logging.info("Created server")
    srv.hosts[RADIUS_CLIENT] = server.RemoteHost(
        RADIUS_CLIENT, RADIUS_SECRET, "cap-test"
    )
    srv.BindToAddress(RADIUS_HOST)
    logging.info(f"Start RADIUS server on {RADIUS_HOST}:{RADIUS_PORT}")
    srv.Run()
