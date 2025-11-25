import jmespath
from flask import current_app, request, session


def get_translate(path, replace=None, lang=None, templates={}):
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
        lang = current_app.config.get('LANGUAGE_DEFAULT')

    expression = f"{lang}.{path}"

    # Выполняем поиск перевода
    translation = jmespath.search(expression, language_content)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    if isinstance(translation, str):
        return translation.format(**templates)
    return replace