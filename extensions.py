import jmespath
from flask import session, request, current_app
from flask_caching import Cache


cache = Cache()


def get_translate(path, replace=None, lang=None):
    language_content = current_app.config.get('LANGUAGE_CONTENT')
    supported_languages = list(language_content.keys())

    # Определяем язык: сначала из параметра, затем из сессии, затем из заголовка, и, наконец, по умолчанию
    lang = (
        lang or 
        session.get("user_lang") or 
        request.accept_languages.best_match(supported_languages) or 
        current_app.config.get('LANGUAGE_DEFAULT')
    )
    
    if not replace:
        replace = path

    # Проверяем, поддерживается ли язык, иначе используем язык по умолчанию
    if lang not in language_content:
        lang = language_content

    # Выполняем поиск перевода
    translation = jmespath.search(f"{lang}.{path}", language_content)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    return translation if isinstance(translation, str) else replace
