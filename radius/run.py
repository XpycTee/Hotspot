import argparse
import logging
import os
from pyrad2 import dictionary, server

from core.config.logging import LOG_LEVEL
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
    parser.add_argument(
        '--log-level',
        type=str.upper,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='WARNING',
        help='Set the logging level'
    )
    args = parser.parse_args()
    worker_id = args.worker_id
    
    mapping = logging.getLevelNamesMapping()
    level = mapping.get(args.log_level, LOG_LEVEL)
    logger.setLevel(level)
    
    hosts = {}
    for host, parametres in RADIUS_CLIENTS.items():
        parametres['secret'] = parametres.get('secret').encode()
        hosts[host] = server.RemoteHost(**parametres)

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
