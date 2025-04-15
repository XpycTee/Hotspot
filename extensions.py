import jmespath
from flask import session, request
from flask_caching import Cache

from settings import Config

cache = Cache()


def get_translate(path, replace=None, lang=None):
    supported_languages = Config.LANGUAGE_CONTENT.keys()
    # Определяем язык: сначала из параметра, затем из сессии, затем из заголовка, и, наконец, по умолчанию
    lang = lang or \
           session.get("user_lang") or \
           request.accept_languages.best_match(supported_languages)
    
    if not replace:
        replace = path

    # Проверяем, поддерживается ли язык, иначе используем язык по умолчанию
    if lang not in Config.LANGUAGE_CONTENT:
        lang = Config.LANGUAGE_DEFAULT

    # Выполняем поиск перевода
    translation = jmespath.search(f"{lang}.{path}", Config.LANGUAGE_CONTENT)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    return translation if isinstance(translation, str) else replace
