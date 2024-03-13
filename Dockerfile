FROM python:3.11-alpine

LABEL build_version="Hotspot version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="xpyctee"
LABEL version="${VERSION}"

RUN apk update
RUN apk add --no-cache bash gcc libc-dev linux-headers
RUN apk add --no-cache uwsgi uwsgi-python3

ENV PYTHONUNBUFFERED True

WORKDIR /hotspot
ADD . /hotspot

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

VOLUME /hotspot/config
VOLUME /hotspot/logs

CMD ["uwsgi", "app.ini"]
