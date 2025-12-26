import argparse
import logging
import os
import threading
from pyrad2 import dictionary

from core.config import CONFIG

from core.config.listener import ConfigListener
from core.logging import get_logger
from radius.hotspot import HotspotRADIUS



def configure_argparser():
    radius = CONFIG.radius
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
        '--address', action='append', default=radius.addresses
    )
    parser.add_argument(
        '--port-auth', type=int, default=radius.ports.auth
    )
    parser.add_argument(
        '--port-acct', type=int, default=radius.ports.acct
    )
    parser.add_argument(
        '--port-coa', type=int, default=radius.ports.coa
    )
    return parser


def main():
    parser = configure_argparser()
    args = parser.parse_args()
    worker_id = args.worker_id
    radius_addresses = args.address
    radius_auth_port = args.port_auth
    radius_acct_port = args.port_acct
    radius_coa_port = args.port_coa

    logger = get_logger(f'RADIUS #{worker_id}')

    mapping = logging.getLevelNamesMapping()
    level = mapping.get(args.log_level, CONFIG.logging.level)
    CONFIG.logging.level = level
    
    srv = HotspotRADIUS(
        addresses=radius_addresses,
        authport=radius_auth_port,
        acctport=radius_acct_port,
        coaport=radius_coa_port,
        hosts=CONFIG.radius.hosts,
        dict=dictionary.Dictionary("radius/dictionary/main"), 
        coa_enabled=True,
        worker_id=worker_id
    )

    pid = os.getpid()
    logger.info(f'Started worker with PID {pid}')


    t = threading.Thread(
        target=ConfigListener().run,
        name='redis-config-listener',
        daemon=True
    )
    t.start()

    srv.Run()


if __name__ == "__main__":
    main()
