import argparse
import dataclasses
import logging
import os
import threading
from pyrad2 import dictionary, server

from core.config.logging import LOG_LEVEL
from core.config.radius import RADIUS
from core.redis.config import ConfigListener
from radius.hotspot import HotspotRADIUS
from radius.logging import logger


def configure_argparser():
    parser = argparse.ArgumentParser(description='RADIUS Server runner')
    parser.add_argument(
        '--worker-id',
        type=int,
        default=0,
        help='RADIUS Server worker ID'
    )
    parser.add_argument(
        '--log-level',
        type=str.upper,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='WARNING',
        help='Set the logging level'
    )
    parser.add_argument(
        '--address', action='append', default=RADIUS.addresses
    )
    parser.add_argument(
        '--port-auth', type=int, default=RADIUS.ports.auth
    )
    parser.add_argument(
        '--port-acct', type=int, default=RADIUS.ports.acct
    )
    parser.add_argument(
        '--port-coa', type=int, default=RADIUS.ports.CoA
    )
    return parser


def config_listener(handler):
    listener = ConfigListener(handler)
    listener.run()


def main():
    parser = configure_argparser()
    args = parser.parse_args()
    worker_id = args.worker_id
    radius_addresses = args.address
    radius_auth_port = args.port_auth
    radius_acct_port = args.port_acct
    radius_coa_port = args.port_coa
    
    mapping = logging.getLevelNamesMapping()
    level = mapping.get(args.log_level, LOG_LEVEL)
    logger.setLevel(level)
    
    hosts = {}
    for host, parametres in RADIUS.hosts.items():
        parametres['secret'] = parametres.get('secret').encode()
        hosts[host] = server.RemoteHost(**parametres)

    srv = HotspotRADIUS(
        addresses=radius_addresses,
        authport=radius_auth_port,
        acctport=radius_acct_port,
        coaport=radius_coa_port,
        hosts=hosts,
        dict=dictionary.Dictionary("radius/dictionary/main"), 
        coa_enabled=True
    )

    pid = os.getpid()
    logger.info(f'Started worker #{worker_id} with PID {pid}')


    t = threading.Thread(
        target=config_listener,
        args=(srv.config_handler,),
        name='redis-config-listener',
        daemon=True
    )
    t.start()

    srv.Run()


if __name__ == "__main__":
    main()
