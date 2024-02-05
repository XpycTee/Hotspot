import os

from .pages.auth import auth_bp

from app.database import db

from flask import Flask

from config.settings import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(30).hex()
    app.config.from_object(config_class)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    # Blueprints add here

    return app
