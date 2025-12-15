import argparse
import logging
import os
from pyrad2 import dictionary, server

from core.config import SETTINGS
from radius.server import HotspotRADIUS
from radius.logging import logger


def configure_argparser():
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
    raduis_settings = SETTINGS.get('radius')
    parser.add_argument(
        '--address', action='append', default=raduis_settings.get('addresses')
    )
    radius_ports = raduis_settings.get('ports')
    parser.add_argument(
        '--port-auth', type=int, default=radius_ports.get('auth')
    )
    parser.add_argument(
        '--port-acct', type=int, default=radius_ports.get('acct')
    )
    parser.add_argument(
        '--port-coa', type=int, default=radius_ports.get('CoA')
    )
    return parser


if __name__ == "__main__":
    parser = configure_argparser()
    args = parser.parse_args()
    worker_id = args.worker_id
    radius_addresses = args.address
    radius_auth_port = args.port_auth
    radius_acct_port = args.port_acct
    radius_coa_port = args.port_coa
    
    log_level = SETTINGS.get('log_level')
    mapping = logging.getLevelNamesMapping()
    level = mapping.get(args.log_level, log_level)
    logger.setLevel(level)
    
    hosts = {}
    raduis_settings = SETTINGS.get('radius')
    for host, parametres in raduis_settings['hosts'].items():
        parametres['secret'] = parametres.get('secret').encode()
        hosts[host] = server.RemoteHost(**parametres)

    srv = HotspotRADIUS(
        addresses=radius_addresses,
        authport=radius_auth_port,
        acctport=radius_acct_port,
        coaport=radius_coa_port,
        hosts=hosts,
        dict=dictionary.Dictionary("radius/dictionary"), 
        coa_enabled=True
    )
    pid = os.getpid()
    logger.info(f'Started worker #{worker_id} with PID {pid}')

    srv.Run()
