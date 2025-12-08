from pyrad2 import dictionary, server

from core.logging.logger import logger
from core.config.radius import RADIUS_ACCT_PORT, RADIUS_ADDRESSES, RADIUS_AUTH_PORT, RADIUS_CLIENTS, RADIUS_COA_PORT
from radius.server import HotspotRADIUS


if __name__ == "__main__":
    hosts = {}
    for client in RADIUS_CLIENTS:
        name = client.get('name')
        host = client.get('host')
        secret = client.get('secret').encode()
        hosts[host] = server.RemoteHost(
            host, secret, name
        )

    srv = HotspotRADIUS(
        addresses=RADIUS_ADDRESSES,
        authport=RADIUS_AUTH_PORT,
        acctport=RADIUS_ACCT_PORT,
        coaport=RADIUS_COA_PORT,
        hosts=hosts,
        dict=dictionary.Dictionary("radius/dictionary"), 
        coa_enabled=True
    )
    logger.info("Created server")
    
    logger.info(f"Start Auth RADIUS server on { 
        '; '.join(
            [f'[{addr}]:{RADIUS_AUTH_PORT}' for addr in RADIUS_ADDRESSES]
        ) 
    }")
    srv.Run()
