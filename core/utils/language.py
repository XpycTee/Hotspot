import jmespath

from core.config import CONFIG


def get_translate(path, lang=None, replace=None, templates={}):
    content = CONFIG.lanugage.content
    language = CONFIG.lanugage.name
    
    if lang is None:
        lang = language
    else:
        lang = lang if lang in content else language

    if not replace:
        replace = path

    expression = f"{lang}.{path}"

    # Выполняем поиск перевода
    translation = jmespath.search(expression, content)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    if isinstance(translation, str):
        return translation.format(**templates)
    return f"{replace}" + (f"?templates={str(templates)}" if templates else "")