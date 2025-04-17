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
RUN apk add --no-cache bash gcc libc-dev linux-headers memcached \
    && pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .
RUN chmod +x ./entrypoint.sh

# Указываем порты и монтируемые директории
EXPOSE 8080
VOLUME /hotspot/config
VOLUME /hotspot/logs

# Используем entrypoint.sh для запуска
ENTRYPOINT ["./entrypoint.sh"]
