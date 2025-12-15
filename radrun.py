# radrun_launcher.py
import logging
import subprocess
import argparse
import os
import sys

from core.config import SETTINGS
from core.config.logging import LOG_LEVEL
from core.config.radius import RADIUS_ACCT_PORT, RADIUS_ADDRESSES, RADIUS_AUTH_PORT, RADIUS_COA_PORT
from radius.logging import logger


def main():
    parser = argparse.ArgumentParser(description='Launcher for RADIUS server workers')
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=int(os.getenv('RADIUS_WORKERS', 4)),
        help='Number of RADIUS worker processes to start'
    )
    parser.add_argument(
        '--log-level',
        type=str.upper,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='WARNING',
        help='Set the logging level'
    )
    args = parser.parse_args()
    num_workers = args.workers

    mapping = logging.getLevelNamesMapping()
    level = mapping.get(args.log_level, LOG_LEVEL)
    logger.setLevel(level)

    logger.info(f'Starting RADIUS server with {num_workers} workers...')
    radius_settings = SETTINGS.get('radius')
    addresses = radius_settings.get('addresses')
    auth_port = radius_settings['ports'].get('auth')
    acct_port = radius_settings['ports'].get('acct')
    coa_port = radius_settings['ports'].get('CoA')
    for address in addresses:
        address = f'[{address}]' if ':' in address else address
        logger.info(f'RADIUS Auth server Listening at: {address}:{auth_port}')
        logger.info(f'RADIUS Accounting  Listening at: {address}:{acct_port}')
        logger.info(f'RADIUS CoA server  Listening at: {address}:{coa_port}')

    processes = []
    try:
        for i in range(num_workers):
            cmd = ['python', '-m', 'radius.run', 
                   '--worker-id', str(i), 
                   '--log-level', args.log_level,
                   '--port-auth', auth_port,
                   '--port-acct', acct_port,
                   '--port-coa', coa_port]
            for address in addresses:
                cmd.extend(['--address', address])
            p = subprocess.Popen(cmd)
            processes.append(p)

        # Ждём завершения всех процессов
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        logger.info('Shutting down workers...')
        for p in processes:
            p.terminate()
        sys.exit(0)

if __name__ == '__main__':
    main()
