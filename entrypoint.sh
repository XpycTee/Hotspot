#!/bin/sh

DEBUG=${DEBUG:-false}

CACHE_SIZE=${CACHE_SIZE:-1024}

if [ -z "$HOTSPOT_CACHE_URL" ]; then
    echo "Using local memcached"
    #memcached -d -u nobody -m $CACHE_SIZE -s "/tmp/memcached.sock"
else
    echo "Using external cache: $HOTSPOT_CACHE_URL"
fi

if [ "$HOTSPOT_RADIUS_ENABLED" = "true" ]; then
    echo "Start RADIUS Auth Server"
    python radrun.py &
fi


# Проверяем наличие переменной окружения FLASK_SECRET_KEY
if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "SECRET_KEY not found. Generating a new one..."
    FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    export FLASK_SECRET_KEY
    echo "Flask Secret key Generated"
fi

# Устанавливаем параметры Gunicorn из переменных окружения или используем значения по умолчанию
GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
GUNICORN_LOG_LEVEL=${LOG_LEVEL:-info}
GUNICORN_PORT=${GUNICORN_PORT:-3000}
GUNICORN_ADDR=${GUNICORN_BIND:-[::]}

echo "Start GUNICORN Server"
exec gunicorn -w "$GUNICORN_WORKERS" -b "$GUNICORN_ADDR:$GUNICORN_PORT" --log-level="$GUNICORN_LOG_LEVEL" webrun:flask_app
