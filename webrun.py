import os


if os.getenv('USE_GEVENT_MONKEY_PATCH', 'true').lower() in {'1', 'true', 'yes'}:
    try:
        from gevent import monkey
        monkey.patch_all()
    except ImportError:
        pass


from web import create_app


flask_app = create_app()


if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=3000, debug=True)
