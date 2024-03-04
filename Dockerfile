FROM python:3.11

LABEL build_version="Hotspot version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="xpyctee"
LABEL version="${VERSION}"

ENV PYTHONUNBUFFERED True


WORKDIR /hotspot
RUN mkdir config
VOLUME ./config

ADD . /hotspot

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uwsgi", "app.ini"]
