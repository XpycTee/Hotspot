#!/bin/bash

# Используем 'set -e' для немедленного выхода при ошибке
set -e
set -o pipefail

# Значения по умолчанию
REGISTRY="xpyctee"
IMAGE="hotspot-mikrotik"
DB_BACKENDS=("sqlite" "postgres" "mysql") # Список поддерживаемых бэкендов

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
  local db_backend=$2
  local backend_tag=$db_backend

  # Формируем базовый тег
  local tags=("-t" "${REGISTRY}/${IMAGE}:${version}-${backend_tag}")

  # Добавляем дополнительные теги
  case $version in
    *rc*)
      [[ $db_backend == "sqlite" ]] && tags+=("-t" "${REGISTRY}/${IMAGE}:test")
      ;;
    *)
      [[ $db_backend == "sqlite" ]] && tags+=("-t" "${REGISTRY}/${IMAGE}:latest")
      tags+=("-t" "${REGISTRY}/${IMAGE}:${backend_tag}")
      ;;
  esac

  # Логируем и выполняем сборку
  echo "Building Docker image with tags: ${tags[*]}"
  docker build \
    --build-arg VERSION="${version}" \
    --build-arg BUILD_DATE="${DATE}" \
    --build-arg DB_BACKEND="${db_backend}" \
    "${tags[@]}" . | tee -a logs/build.log
}

# Основная функция
main() {
  parse_args "$@"
  local version
  version=$(get_version)

  # Сборка образов для каждого бэкенда
  for db_backend in "${DB_BACKENDS[@]}"; do
    echo "Building image for database backend: $db_backend"
    build_docker_image "$version" "$db_backend"
  done

  # Используем 'awk' для более точного поиска
  docker images | awk -v image="$IMAGE" '$1 ~ image'
}

main "$@"