import argparse
import os
from pyrad2 import dictionary, server

from core.config.radius import RADIUS_ACCT_PORT, RADIUS_ADDRESSES, RADIUS_AUTH_PORT, RADIUS_CLIENTS, RADIUS_COA_PORT
from radius.server import HotspotRADIUS
from radius.logging import logger


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='RADIUS Server runner')
    parser.add_argument(
        '--worker-id',
        type=int,
        help='RADIUS Server worker ID'
    )
    args = parser.parse_args()
    worker_id = args.worker_id
    
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
    pid = os.getpid()
    logger.info(f'Started worker #{worker_id} with PID {pid}')

    srv.Run()
