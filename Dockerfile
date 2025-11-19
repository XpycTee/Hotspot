# Используем более стабильную версию Python
FROM python:3.13-alpine

# Указываем метаданные
LABEL maintainer="xpyctee"
LABEL build_version="Hotspot version: ${VERSION} Build-date: ${BUILD_DATE}"
LABEL version="${VERSION}"

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /hotspot

# Устанавливаем системные и Python зависимости
COPY requirements.txt ./
RUN apk update \
    && apk add --no-cache bash gcc libc-dev linux-headers memcached \
    && pip install --no-cache-dir -r requirements.txt

# Устанавливаем зависимости для конкретного бэкенда
ARG DB_BACKEND
COPY requirements-postgres.txt ./
COPY requirements-mysql.txt ./
RUN if [ "$DB_BACKEND" = "postgres" ]; then \
      pip install --no-cache-dir -r requirements-postgres.txt; \
    elif [ "$DB_BACKEND" = "mysql" ]; then \
      apk add --virtual build-deps python3-dev musl-dev && \
      apk add --no-cache mariadb-dev; \
      pip install --no-cache-dir -r requirements-mysql.txt; \
      apk del build-deps; \
    fi

# Копируем остальные файлы проекта
COPY . .
RUN chmod +x ./entrypoint.sh

# Указываем порты и монтируемые директории
EXPOSE 8080
VOLUME /hotspot/config

# Используем entrypoint.sh для запуска
ENTRYPOINT ["./entrypoint.sh"]