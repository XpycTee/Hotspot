# logger.py
from flask import current_app, request, session

def _format_msg(text):
    sess_id = session.get('_id')
    endpoint = request.endpoint
    short_sess_id = str(sess_id)[:8] if sess_id else 'no-session'
    return f"[{short_sess_id}:{endpoint}] {text}"

def debug(msg, *args, **kwargs):
    current_app.logger.debug(_format_msg(msg), *args, **kwargs)

def info(msg, *args, **kwargs):
    current_app.logger.info(_format_msg(msg), *args, **kwargs)

def warning(msg, *args, **kwargs):
    current_app.logger.warning(_format_msg(msg), *args, **kwargs)

def error(msg, *args, **kwargs):
    current_app.logger.error(_format_msg(msg), *args, **kwargs)
