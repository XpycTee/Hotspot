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
        'SMSRU_API_KEY'
    ]
    missing_vars = [env_var for env_var in required_env_vars if env_var not in os.environ]

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
