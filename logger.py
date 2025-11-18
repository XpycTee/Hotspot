# logger.py
from flask import current_app, session, request

def _format_msg(text):
    sess_id = session.get('_id')
    endpoint = request.endpoint
    return f"[{sess_id[8]}:{endpoint}] {text}"

def debug(msg, *args, **kwargs):
    current_app.logger.debug(_format_msg(msg), *args, **kwargs)

def info(msg, *args, **kwargs):
    current_app.logger.info(_format_msg(msg), *args, **kwargs)

def warning(msg, *args, **kwargs):
    current_app.logger.warning(_format_msg(msg), *args, **kwargs)

def error(msg, *args, **kwargs):
    current_app.logger.error(_format_msg(msg), *args, **kwargs)
