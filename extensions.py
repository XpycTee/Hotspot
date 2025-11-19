import json
import re
import ssl
import certifi
import jmespath
from flask import session, request, current_app
from flask_caching import Cache
import urllib


cache = Cache()


@cache.memoize(timeout=1 * 60 * 60)  # Кешируем результат на 1 час
def fetch_employees():
    """Функция для получения данных сотрудников из внешнего ресурса."""
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen('https://is.sova72.ru/documents/employee/phonebook.json', context=context) as response:
        return json.load(response)


def normalize_phone(phone_number: str) -> str:
    """Normalize phone to digits, leading 7 for Russia-style numbers."""
    if not phone_number:
        return ''
    num = re.sub(r'\D', '', phone_number)
    num = re.sub(r'^8', '7', num)
    if num.startswith('07'):  # guard: if weird leading zero
        num = '7' + num[2:]
    return num


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
        lang = current_app.config.get('LANGUAGE_DEFAULT')

    expression = f"{lang}.{path}"

    # Выполняем поиск перевода
    translation = jmespath.search(expression, language_content)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    return translation if isinstance(translation, str) else replace
