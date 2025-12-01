import jmespath

from core.config.language import LANGUAGE_CONTENT, LANGUAGE_DEFAULT


def get_translate(path, lang="en", replace=None, templates={}):
    language_content = LANGUAGE_CONTENT

    lang = lang if lang in language_content else LANGUAGE_DEFAULT

    if not replace:
        replace = path

    expression = f"{lang}.{path}"

    # Выполняем поиск перевода
    translation = jmespath.search(expression, language_content)

    # Возвращаем перевод, если он найден, иначе возвращаем исходный путь
    if isinstance(translation, str):
        return translation.format(**templates)
    return f"{replace}" + (f"?templates={str(templates)}" if templates else "")