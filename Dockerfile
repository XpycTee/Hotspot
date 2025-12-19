FROM python:3.13-alpine

LABEL maintainer="xpyctee"
LABEL build_version="Hotspot version: ${VERSION} Build-date: ${BUILD_DATE}"
LABEL version="${VERSION}"

ENV PYTHONUNBUFFERED=1

WORKDIR /hotspot

#########################################
# 1. Базовые системные зависимости
#########################################

RUN apk update && apk add --no-cache \
    bash \
    gcc \
    libc-dev \
    linux-headers \
    tzdata

#########################################
# 2. Опциональные backend'ы
#########################################

ARG ENABLE_REDIS=true
ARG ENABLE_MEMCACHED=false

RUN if [ "$ENABLE_REDIS" = "true" ]; then \
        apk add --no-cache redis; \
    fi

RUN if [ "$ENABLE_MEMCACHED" = "true" ]; then \
        apk add --no-cache memcached; \
    fi

#########################################
# 3. Python зависимости
#########################################

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

#########################################
# 4. DB backend (опционально)
#########################################

ARG DB_BACKEND
COPY requirements-postgres.txt ./
COPY requirements-mysql.txt ./

RUN if [ "$DB_BACKEND" = "postgres" ]; then \
        pip install --no-cache-dir -r requirements-postgres.txt; \
    elif [ "$DB_BACKEND" = "mysql" ]; then \
        apk add --virtual .build-deps python3-dev musl-dev mariadb-dev && \
        pip install --no-cache-dir -r requirements-mysql.txt && \
        apk del .build-deps; \
    fi

#########################################
# 5. Код проекта
#########################################

COPY . .
RUN chmod +x ./entrypoint.sh

#########################################
# 6. Runtime
#########################################

EXPOSE 8080
EXPOSE 1812/udp
EXPOSE 1813/udp
EXPOSE 3799/udp

ENTRYPOINT ["./entrypoint.sh"]
