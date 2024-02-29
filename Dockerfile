FROM python:3.11

LABEL build_version="Hotspot version:- ${VERSION} Build-date:- ${BUILD_DATE}"
LABEL maintainer="xpyctee"
LABEL version="${VERSION}"

ENV PYTHONUNBUFFERED True

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . ./hotspot
WORKDIR /hotspot

RUN mkdir config
VOLUME ./config

ENTRYPOINT ["python", "./app.py"]
