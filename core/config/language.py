import json
import os

from environs import Env

from core.config import SETTINGS


env = Env()
env.read_env()


def load_language_files():
    language_folder = 'web/static/language'
    language_content = {}
    for filename in os.listdir(language_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(language_folder, filename)
            language_name = os.path.splitext(filename)[0]
            with open(file_path, 'r', encoding='utf-8') as lang_file:
                language_content[language_name] = json.load(lang_file)
    return language_content


LANGUAGE_DEFAULT = env.str('HOTSPOT_LANGUAGE', SETTINGS.get('language', 'en'))
LANGUAGE_CONTENT = load_language_files()
