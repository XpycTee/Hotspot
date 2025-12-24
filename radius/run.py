import argparse
import logging
import os
import threading
from pyrad2 import dictionary, server

from core.config import CONFIG, ConfigStore
from core.config.logging import LOG_LEVEL
from core.config.radius import RADIUS
from core.redis.config import ConfigListener
from radius.hotspot import HotspotRADIUS
from radius.logging import logger


config_lock = threading.RLock()


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
        '--port-coa', type=int, default=RADIUS.ports.coa
    )
    return parser


def config_handler(update: dict, store: ConfigStore):
    with config_lock:
        logger.debug(update)
        up_version = update.get('version')
        if up_version <= CONFIG.version:
            return  # устаревшее событие
        
        new_cfg = store.load()
        logger.debug(new_cfg)
        
        updated_hosts = new_cfg.get('hosts')

        deleted_hosts = set(RADIUS.hosts) - set(updated_hosts)
        for host in deleted_hosts:
            del RADIUS.hosts[host]

        for host, parametres in updated_hosts.items():
            RADIUS.hosts[host] = server.RemoteHost(**parametres)

        CONFIG.version = up_version


def config_listener():
    listener = ConfigListener(handelr=config_handler, domain='radius')
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
    
    srv = HotspotRADIUS(
        addresses=radius_addresses,
        authport=radius_auth_port,
        acctport=radius_acct_port,
        coaport=radius_coa_port,
        hosts=RADIUS.hosts,
        dict=dictionary.Dictionary("radius/dictionary/main"), 
        coa_enabled=True
    )

    pid = os.getpid()
    logger.info(f'Started worker #{worker_id} with PID {pid}')


    t = threading.Thread(
        target=config_listener,
        name='redis-config-listener',
        daemon=True
    )
    t.start()

    srv.Run()


if __name__ == "__main__":
    main()
