import argparse
import os
import threading
from pyrad2 import dictionary

from core.config import get_config, init_config, runtime_listener
from core.logging import get_logger
from radius.hotspot import HotspotRADIUS


def configure_argparser():
    radius = get_config().radius
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


def run_runtime_listener(handler):
    t = threading.Thread(
        target=runtime_listener,
        args=(handler,),
        name='redis-config-listener',
        daemon=True
    )
    t.start()


def main():
    cfg = init_config('radius')

    parser = configure_argparser()
    args = parser.parse_args()
    worker_id = args.worker_id
    radius_addresses = args.address
    radius_auth_port = args.port_auth
    radius_acct_port = args.port_acct
    radius_coa_port = args.port_coa
    
    srv = HotspotRADIUS(
        addresses=radius_addresses,
        authport=radius_auth_port,
        acctport=radius_acct_port,
        coaport=radius_coa_port,
        hosts=cfg.radius.hosts,
        dict=dictionary.Dictionary("radius/dictionary/main"), 
        coa_enabled=True,
        worker_id=worker_id
    )

    pid = os.getpid()
    logger = get_logger(f'RADIUS #{worker_id}')
    logger.info(f'Started worker with PID {pid}')

    run_runtime_listener(srv.update_hosts)

    srv.Run()


if __name__ == "__main__":
    main()
