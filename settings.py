import json
import os
import yaml
import bcrypt

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SETTINGS_FILE_PATH = "config/settings.yaml"
    LANGUAGE_FOLDER = "web/static/language"
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin'
    DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS = 3
    DEFAULT_ADMIN_LOCKOUT_TIME = 5
    DEFAULT_COMPANY_NAME = 'Default Company'

    # Переменные класса для хранения конфигурации
    ADMIN = None
    SECRET_KEY = None
    LANGUAGE_DEFAULT = None
    LANGUAGE_CONTENT = None
    COMPANY_NAME = None
    DEBUG = None

    @classmethod
    def init_app(cls, app):
        cls.settings = cls.load_settings()
        cls.ADMIN = cls.configure_admin()
        cls.SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', cls.settings.get('flask_secret_key'))
        cls.LANGUAGE_DEFAULT = os.environ.get('HOTSPOT_LANGUAGE', cls.settings.get('language', 'en'))
        cls.LANGUAGE_CONTENT = cls.load_language_files()
        cls.COMPANY_NAME = os.environ.get('HOTSPOT_COMPANY_NAME', cls.settings.get('company_name', cls.DEFAULT_COMPANY_NAME))
        cls.DEBUG = os.environ.get('DEBUG', cls.settings.get('debug', False))

        app.config.from_object(cls)

    @classmethod
    def load_settings(cls):
        with open(cls.SETTINGS_FILE_PATH, "r", encoding="utf-8") as settings_file:
            return yaml.safe_load(settings_file).get('settings', {})

    @classmethod
    def configure_admin(cls):
        admin_settings = cls.settings.get('admin', {})
        admin_user = admin_settings.get('user', {})
        username = os.environ.get('HOTSPOT_ADMIN_USERNAME', admin_user.get('username', cls.DEFAULT_ADMIN_USERNAME))
        password = os.environ.get('HOTSPOT_ADMIN_PASSWORD', admin_user.get('password', cls.DEFAULT_ADMIN_PASSWORD))
        max_login_attempts = os.environ.get('HOTSPOT_ADMIN_MAX_LOGIN_ATTEMPTS', admin_settings.get('max_login_attempts', cls.DEFAULT_ADMIN_MAX_LOGIN_ATTEMPTS))
        lockout_time = os.environ.get('HOTSPOT_ADMIN_LOCKOUT_TIME', admin_settings.get('lockout_time', cls.DEFAULT_ADMIN_LOCKOUT_TIME))
        password_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return {
            'username': username, 
            'password': password_hashed, 
            'max_login_attempts': int(max_login_attempts), 
            'lockout_time': int(lockout_time)
        }

    @classmethod
    def load_language_files(cls):
        language_content = {}
        for filename in os.listdir(cls.LANGUAGE_FOLDER):
            if filename.endswith(".json"):
                file_path = os.path.join(cls.LANGUAGE_FOLDER, filename)
                language_name = os.path.splitext(filename)[0]
                with open(file_path, "r", encoding='utf-8') as lang_file:
                    language_content[language_name] = json.load(lang_file)
        return language_content
       