import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    _default_sql_url = 'sqlite:///' + os.path.join(basedir, 'app/database/hotspot.db')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or _default_sql_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SMSRU_API_KEY = os.environ.get('SMSRU_API_KEY')
    HOTSPOT_USER = os.environ.get('HOTSPOT_USER') or 'guest'
    HOTSPOT_PASS = os.environ.get('HOTSPOT_PASS') or 'secret'
    COMPANY_NAME = 'ООО "Рога и копыта"'
