#!/bin/bash

set -o pipefail

REGISTRY=containers.xpyctee.ru
IMAGE=hotspot-sova

DATE=$(date '+%Y-%m-%d')

if [[ $(git describe --tags --abbrev=0) == *rc* ]]
then
VERSION=$(git describe --tags --abbrev=0)-build$(git rev-list --all --count)
docker build --build-arg=VERSION=${VERSION} --build-arg=BUILD_DATE=${DATE} -t ${REGISTRY}/${IMAGE}:${VERSION} . | tee logs/build.log || exit 1
else
VERSION=$(git describe --tags --abbrev=0)
docker build --build-arg=VERSION=${VERSION} --build-arg=BUILD_DATE=${DATE} -t ${REGISTRY}/${IMAGE}:${VERSION} -t ${REGISTRY}/${IMAGE}:latest . | tee logs/build.log || exit 1
fi


docker images | grep ${IMAGE}
