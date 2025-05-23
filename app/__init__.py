import os
import logging

from app.pages.auth import auth_bp
from app.pages.admin import admin_bp
from app.pages.error import error_bp

from app.database import db

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from settings import Config
from extensions import cache, get_translate


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
    
    init = check_required_env(required_env_vars)

    if init:
        app = Flask(__name__)

        config_class.init_app(app)
        
        # Настройка логгирования для устранения дублирования
        gunicorn_error_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_error_logger.handlers  # Используем только обработчики gunicorn
        app.logger.setLevel(gunicorn_error_logger.level)  # Устанавливаем уровень логирования gunicorn

        if app.debug:
            app.logger.setLevel(logging.DEBUG)
        
        app.json = CustomJSONProvider(app)

        db.init_app(app)
        cache.init_app(app)

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(error_bp)

        with app.app_context():
            db.create_all()

        # Добавляем контекстный процессор
        @app.context_processor
        def inject_get_translate():
            return dict(get_translate=get_translate)

        return app
    return None
