import logging
import os
import time

from gists import str2bool

DEBUG = str2bool(os.environ['DEBUG']) if 'DEBUG' in os.environ else False


def init():
    log = logging.getLogger()
    log.setLevel(logging.DEBUG if DEBUG else logging.INFO)  # Set log level based on DEBUG flag

    # Configure a stream handler with a formatter
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter.converter = time.localtime
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    # Check for required environment variables
    required_env_vars = [
        [
            'SMSRU_SENDER_CFG',
            'MIKROTIK_SENDER_CFG',
            'HUAWEI_SENDER_CFG'
        ],
        'COMPANY_NAME'
    ]

    missing_vars = []

    for env_var in required_env_vars:
        if isinstance(env_var, list):
            if not any(key in os.environ for key in env_var):
                missing_vars.append(env_var)
        else:
            if env_var not in os.environ:
                missing_vars.append(env_var)

    # Log an error for missing variables and return False if any are not set
    if missing_vars:
        log.error(f'Required environment variables not set: {", ".join(missing_vars)}')
        return False

    return True


if __name__ == '__main__':
    if init():
        # START HERE
        from app import create_app

        flask_app = create_app()
        flask_app.run(port=3000, debug=DEBUG)
