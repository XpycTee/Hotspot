import bcrypt
from environs import Env

from core.config import SETTINGS, convert_delay

env = Env(prefix='HOTSPOT_')
env.read_env()

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'
DEFAULT_MAX_LOGIN_ATTEMPTS = 3
DEFAULT_LOCKOUT_TIME = 300

def configure_admin():
    admin = SETTINGS.get('admin')
    with env.prefixed('ADMIN_'):
        username = env.str('USERNAME', admin.get('username', DEFAULT_USERNAME))
        password = env.str('PASSWORD', admin.get('password', DEFAULT_PASSWORD))
        max_login_attempts = env.int('MAX_LOGIN_ATTEMPTS', admin.get('max_login_attempts', DEFAULT_MAX_LOGIN_ATTEMPTS))
        lockout_time = env.int('LOCKOUT_TIME', admin.get('lockout_time', DEFAULT_LOCKOUT_TIME))

    password_hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return {
        'username': username, 
        'password': password_hashed, 
        'max_login_attempts': max_login_attempts, 
        'lockout_time': lockout_time
    }

ADMIN = configure_admin()