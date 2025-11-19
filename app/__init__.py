from app.pages import pages_bp

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

    app.register_blueprint(pages_bp)

    with app.app_context():
        db.create_all()

    # Добавляем контекстный процессор
    @app.context_processor
    def inject_get_translate():
        return dict(get_translate=get_translate)

    return app
