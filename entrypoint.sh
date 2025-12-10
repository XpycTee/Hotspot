#!/bin/sh
set -e

DEBUG=${DEBUG:-false}
CACHE_SIZE=${CACHE_SIZE:-1024}

echo "=== HOTSPOT ENTRYPOINT STARTED ==="

#########################################
# 1. Memcached (локальный / внешний)
#########################################

if [ -z "$HOTSPOT_CACHE_URL" ]; then
    echo "Starting local memcached (no HOTSPOT_CACHE_URL provided)"
    memcached -u nobody -m "$CACHE_SIZE" -s "/tmp/memcached.sock" &
    MEMCACHED_PID=$!
else
    echo "Using external cache: $HOTSPOT_CACHE_URL"
fi


#########################################
# 2. Ининциализация базы данных
#########################################

echo "Running DB initialization..."
python init_database.py


#########################################
# 3. RADIUS Server
#########################################

RADIUS_ENABLED=${RADIUS_ENABLED:-true}
RADIUS_WORKERS=${RADIUS_WORKERS:-4}

if [ "$RADIUS_ENABLED" = "true" ]; then
    python radrun.py -w "$RADIUS_WORKERS" &
    RADIUS_PID=$!
else
    echo "RADIUS disabled"
fi


#########################################
# 4. Flask Secret Key
#########################################

if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "SECRET_KEY not found. Generating new one..."
    FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    export FLASK_SECRET_KEY
    echo "Generated new Flask SECRET_KEY"
fi


#########################################
# 5. Gunicorn
#########################################

GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
GUNICORN_LOG_LEVEL=${LOG_LEVEL:-info}
GUNICORN_PORT=${GUNICORN_PORT:-8080}
GUNICORN_ADDR=${GUNICORN_BIND:-[::]}

echo "Starting Gunicorn web server..."
echo "Workers: $GUNICORN_WORKERS"
echo "Bind: $GUNICORN_ADDR:$GUNICORN_PORT"
echo "Log level: $GUNICORN_LOG_LEVEL"

exec gunicorn \
    -w "$GUNICORN_WORKERS" \
    -b "$GUNICORN_ADDR:$GUNICORN_PORT" \
    --log-level="$GUNICORN_LOG_LEVEL" \
    webrun:flask_app
