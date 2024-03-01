FROM python:3.11-bullseye

LABEL build_version="Hotspot version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="xpyctee"
LABEL version="${VERSION}"

ENV PYTHONUNBUFFERED True


WORKDIR /hotspot
RUN mkdir config
RUN mkdir logs

VOLUME ./config
VOLUME ./logs

ADD . /hotspot

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uwsgi", "app.ini"]
