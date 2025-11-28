import os
import logging

from web.pages import pages_bp

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from core import database
from core.utils.language import get_translate
from web.settings import Config

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

class CustomJSONProvider(DefaultJSONProvider):
    ensure_ascii = False


def create_app(config_class=Config):
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

     # Check for required environment variables
    required_env_vars = []
    
    init_logger = logging.getLogger("Init")
    configure_logger(init_logger)

    init = check_required_env(required_env_vars, init_logger)

    if init:
        app = Flask(__name__)

        config_class.init_app(app)
        
        configure_logger(app.logger)
        
        app.json = CustomJSONProvider(app)

        database.create_all()

        app.register_blueprint(pages_bp)

        # Добавляем контекстный процессор
        @app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)

        return app
    return None
