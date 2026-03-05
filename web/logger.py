import logging

from flask import current_app, has_app_context, has_request_context, request, session

def _format_msg(text):
    sess_id = None
    endpoint = None
    if has_request_context():
        sess_id = session.get('_id')
        endpoint = request.endpoint
    short_sess_id = str(sess_id)[:8] if sess_id else 'no-session'
    endpoint = endpoint or 'no-endpoint'
    return f"[{short_sess_id}:{endpoint}] {text}"


def _get_logger():
    if has_app_context():
        return current_app.logger
    return logging.getLogger('web.logger')

def debug(msg, *args, **kwargs):
    _get_logger().debug(_format_msg(msg), *args, **kwargs)

def info(msg, *args, **kwargs):
    _get_logger().info(_format_msg(msg), *args, **kwargs)

def warning(msg, *args, **kwargs):
    _get_logger().warning(_format_msg(msg), *args, **kwargs)

def error(msg, *args, **kwargs):
    _get_logger().error(_format_msg(msg), *args, **kwargs)
