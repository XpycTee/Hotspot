import os
import logging

from app.pages.auth import auth_bp
from app.pages.error import error_bp

from app.database import db

from flask import Flask

from settings import Config


def check_required_env(required: list, logger=logging.getLogger()) -> bool:
    missing_vars = []
    env_keys = set(os.environ.keys())
    for env_var in required:
        if isinstance(env_var, list):
            if not any(key in env_keys for key in env_var):
                missing_vars.append(env_var)
        else:
            if env_var not in env_keys:
                missing_vars.append(env_var)
    
    if missing_vars:
        flat_missing_vars = [var if isinstance(var, str) else "/".join(var) for var in missing_vars]
        logger.error(f'Required environment variables not set: {", ".join(flat_missing_vars)}')
        return False

    return True


def create_app(config_class=Config):

    default_handler = logging.StreamHandler()
    default_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
    )

    logger = logging.getLogger()
    logger.addHandler(default_handler)

     # Check for required environment variables
    required_env_vars = []
    
    init = check_required_env(required_env_vars, logger)

    if init:
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
