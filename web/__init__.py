import os
import logging

from core.config import get_config, init_config
from core.logging import get_logger
from web.pages import pages_bp
from web.webhooks import webhooks_bp
from web.api import api_bp

from flask import Flask
from flask.json.provider import DefaultJSONProvider

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
    # Check for required environment variables
    required_env_vars = []
    
    init_logger = get_logger("Init")

    init = check_required_env(required_env_vars, init_logger)

    if init:
        init_config('web')

        app = Flask(__name__)

        config_class.init_app(app)
        
        app.json = CustomJSONProvider(app)

        app.register_blueprint(pages_bp)
        app.register_blueprint(webhooks_bp)
        app.register_blueprint(api_bp)

        # Добавляем контекстный процессор
        @app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)

        @app.context_processor
        def inject_get_config():
            return dict(get_config=get_config)

        return app
    return None
