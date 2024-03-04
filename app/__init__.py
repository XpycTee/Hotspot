import logging
import os
import time

from .pages.auth import auth_bp
from .pages.error import error_bp

from app.database import db

from flask import Flask

from settings import Config


def str2bool(string: str | bool) -> bool:
    if isinstance(string, bool):
        return string
    lower_string = string.lower() if isinstance(string, str) else str(string).lower()
    return lower_string not in ('false', '0', 'no', 'n')


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
    required_env_vars = []

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


def create_app(config_class=Config):
    if init():
        app = Flask(__name__)
        app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(30).hex()
        app.config.from_object(config_class)

        db.init_app(app)

        app.register_blueprint(auth_bp)
        app.register_blueprint(error_bp)
        # Blueprints add here
        with app.app_context():
            db.create_all()
        return app
