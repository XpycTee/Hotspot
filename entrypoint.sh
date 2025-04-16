#!/bin/sh

# Проверяем значение переменной DEBUG
if [ "$DEBUG" = "true" ]; then
    exec gunicorn -w 4 -b 0.0.0.0:8080 --reload --log-level=debug main:flask_app
else
    exec gunicorn -w 4 -b 0.0.0.0:8080 main:flask_app
fi
