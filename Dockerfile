FROM python:3.13-alpine

LABEL build_version="Hotspot version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="xpyctee"
LABEL version="${VERSION}"

# Устанавливаем системные зависимости
RUN apk add --no-cache bash gcc libc-dev linux-headers \
    && apk update \
    && apk upgrade

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=True

# Устанавливаем рабочую директорию
WORKDIR /hotspot

# Копируем только requirements.txt для кэширования зависимостей
COPY requirements.txt /hotspot/requirements.txt

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . /hotspot

# Указываем порты и монтируемые директории
EXPOSE 8080
VOLUME /hotspot/config
VOLUME /hotspot/logs

# Используем Gunicorn для запуска приложения
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "main:flask_app"]
