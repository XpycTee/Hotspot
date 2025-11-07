import uuid
from app.database.models import WifiClient
from app.pages.auth import auth_bp
from app.pages.admin import admin_bp
from app.pages.error import error_bp

from app.database import db

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from settings import Config
from extensions import cache, get_translate


class CustomJSONProvider(DefaultJSONProvider):
    ensure_ascii = False


def create_app(config_class=Config):
    app = Flask(__name__)

    config_class.init_app(app)
    
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
