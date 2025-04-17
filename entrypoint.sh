#!/bin/sh

# Путь к файлу-маркеру
INIT_FLAG="/hotspot/.db_initialized"

# Проверяем, была ли уже выполнена инициализация
if [ ! -f "$INIT_FLAG" ]; then
    echo "Initializing the database for the first time..."
    python ./init_database.py
    echo "Database initialized. Creating marker file."
    touch "$INIT_FLAG"
else
    echo "Database already initialized. Skipping initialization."
fi

# Проверяем наличие переменной окружения SECRET_KEY
if [ -z "$FLASK_SECRET_KEY" ]; then
    echo "SECRET_KEY not found. Generating a new one..."
    FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    export FLASK_SECRET_KEY
    echo "Generated SECRET_KEY: $FLASK_SECRET_KEY"
fi

# Устанавливаем параметры Gunicorn из переменных окружения или используем значения по умолчанию
GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-info}
GUNICORN_PORT=${GUNICORN_PORT:-8080}
GUNICORN_ADDR=${GUNICORN_BIND:-0.0.0.0}

# Проверяем значение переменной DEBUG
if [ "$DEBUG" = "true" ]; then
    exec gunicorn -w "$GUNICORN_WORKERS" -b "$GUNICORN_ADDR:$GUNICORN_PORT" --reload --log-level=debug main:flask_app
else
    exec gunicorn -w "$GUNICORN_WORKERS" -b "$GUNICORN_ADDR:$GUNICORN_PORT" --log-level="$GUNICORN_LOG_LEVEL" main:flask_app
fi