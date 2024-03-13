#!/bin/bash

set -o pipefail

REGISTRY=localhost
IMAGE=hotspot-mikrotik

DATE=$(date '+%Y-%m-%d')

if [[ $(git describe --tags --abbrev=0) == *rc* ]]
then
VERSION=$(git describe --tags --abbrev=0)-build$(git rev-list --all --count)
else
VERSION=$(git describe --tags --abbrev=0)
fi

docker build --build-arg=VERSION=${VERSION} --build-arg=BUILD_DATE=${DATE} -t ${REGISTRY}/${IMAGE}:${VERSION} -t ${REGISTRY}/${IMAGE}:latest . | tee logs/build.log || exit 1

docker images | grep ${IMAGE}
