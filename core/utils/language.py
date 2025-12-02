import jmespath

from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT


def get_translate(path, lang="en", replace=None, templates={}):
    lang = lang if lang in LANGUAGE_CONTENT else LANGUAGE_DEFAULT

    if not replace:
        replace = path

    expression = f"{lang}.{path}"

    # Выполняем поиск перевода
    translation = jmespath.search(expression, LANGUAGE_CONTENT)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    if isinstance(translation, str):
        return translation.format(**templates)
    return f"{replace}" + (f"?templates={str(templates)}" if templates else "")