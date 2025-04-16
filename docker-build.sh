#!/bin/bash

# Используем 'set -e' для немедленного выхода при ошибке
set -e
set -o pipefail

# Значения по умолчанию
REGISTRY="localhost"
IMAGE="hotspot-mikrotik"

# Функция для обработки аргументов командной строки
parse_args() {
  while getopts "r:i:" opt; do
    case ${opt} in
      r )
        REGISTRY=$OPTARG
        ;;
      i )
        IMAGE=$OPTARG
        ;;
      \? )
        echo "Usage: cmd [-r registry] [-i image]"
        exit 1
        ;;
    esac
  done
}

DATE=$(date '+%Y-%m-%d')

# Функция для получения версии
get_version() {
  local base_version
  base_version=$(git describe --tags --abbrev=0)

  # Используем тернарный оператор для упрощения логики
  [[ $base_version == *rc* ]] && echo "${base_version}-build$(git rev-list --all --count)" || echo "$base_version"
}

# Функция для сборки Docker-образа
build_docker_image() {
  local version=$1
  local tags=("-t" "${REGISTRY}/${IMAGE}:${version}")

  # Добавляем тег 'latest', если версия не содержит '-build'
  [[ $version != *-build* ]] && tags+=("-t" "${REGISTRY}/${IMAGE}:latest")

  # Используем массив для передачи аргументов в 'docker build'
  docker build --build-arg VERSION="${version}" --build-arg BUILD_DATE="${DATE}" "${tags[@]}" . | tee logs/build.log
}

# Основная функция
main() {
  parse_args "$@"
  local version
  version=$(get_version)
  build_docker_image "$version"

  # Используем 'awk' для более точного поиска
  docker images | awk -v image="$IMAGE" '$1 ~ image'
}

main "$@"
