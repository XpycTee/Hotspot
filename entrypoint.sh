#!/bin/sh
set -e

DEBUG=${DEBUG:-false}
CACHE_SIZE=${CACHE_SIZE:-1024}
REDIS_MAXMEMORY=${REDIS_MAXMEMORY:-64mb}

echo "=== HOTSPOT ENTRYPOINT STARTED ==="

#########################################
# 1. Redis (локальный / внешний)
#########################################

if [ -z "$HOTSPOT_REDIS_URL" ]; then
    if command -v redis-server >/dev/null 2>&1; then
        echo "Starting local Redis (no HOTSPOT_REDIS_URL provided)"

        REDIS_SOCKET="/tmp/redis.sock"

        cat > /tmp/redis.conf <<EOF
port 0
unixsocket $REDIS_SOCKET
unixsocketperm 777
save ""
appendonly no
maxmemory $REDIS_MAXMEMORY
maxmemory-policy allkeys-lru
EOF

        redis-server /tmp/redis.conf &
        REDIS_PID=$!

        export HOTSPOT_REDIS_URL="unix://$REDIS_SOCKET?db=0"
    else
        echo "ERROR: Redis not available and HOTSPOT_REDIS_URL not set"
        exit 1
    fi
else
    echo "Using external Redis: $HOTSPOT_REDIS_URL"
fi


#########################################
# 2. Инициализация базы данных
#########################################

echo "Running DB initialization..."
python init_database.py


#########################################
# 3. RADIUS Server
#########################################

RADIUS_ENABLED=${RADIUS_ENABLED:-true}
RADIUS_WORKERS=${RADIUS_WORKERS:-4}
: "${RADIUS_LOG_LEVEL=${LOG_LEVEL:-info}}"

if [ "$RADIUS_ENABLED" = "true" ]; then
    echo "Starting RADIUS ($RADIUS_WORKERS workers)"
    python radrun.py -w "$RADIUS_WORKERS" --log-level "$RADIUS_LOG_LEVEL" &
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
GUNICORN_PORT=${GUNICORN_PORT:-8080}
GUNICORN_ADDR=${GUNICORN_BIND:-[::]}
: "${GUNICORN_LOG_LEVEL=${LOG_LEVEL:-info}}"

echo "Starting Gunicorn web server..."
echo "Workers: $GUNICORN_WORKERS"
echo "Bind: $GUNICORN_ADDR:$GUNICORN_PORT"
echo "Log level: $GUNICORN_LOG_LEVEL"

exec gunicorn \
    -w "$GUNICORN_WORKERS" \
    -b "$GUNICORN_ADDR:$GUNICORN_PORT" \
    --log-level="$GUNICORN_LOG_LEVEL" \
    webrun:flask_app
