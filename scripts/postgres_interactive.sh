#!/usr/bin/env bash
# Postgres コンテナで対話 psql / bash を開く。
# podman-compose の `exec` は `-it` を解釈しないため、Podman 時は compose.yml の
# container_name（equipment-reservation-postgres）へ直接 podman exec する。
# Docker 時は scripts/compose.sh exec -it …（Compose V2 / docker-compose）を使う。
#
# 使い方: postgres_interactive.sh psql | shell
# 本番相当スタックの場合は PERSISTENCE_PROFILE=production を付けて just から呼ぶ。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="${DEV_CONTAINER_RUNTIME:-podman}"
MODE="${1:-}"
POSTGRES_CONTAINER_NAME="equipment-reservation-postgres"

if [[ "$MODE" != "psql" && "$MODE" != "shell" ]]; then
  echo "使い方: $0 psql | shell" >&2
  exit 1
fi

run_docker() {
  cd "$ROOT"
  bash "$ROOT/scripts/compose.sh" exec -it postgres "$@"
}

if [[ "$RUNTIME" == "docker" ]]; then
  if [[ "$MODE" == "psql" ]]; then
    run_docker psql -U dev_user -d equipment_reservation
  else
    run_docker bash
  fi
  exit 0
fi

if [[ "$RUNTIME" != "podman" ]]; then
  echo "DEV_CONTAINER_RUNTIME は docker または podman です（現在: $RUNTIME）。" >&2
  exit 1
fi

if ! podman inspect -t container "$POSTGRES_CONTAINER_NAME" >/dev/null 2>&1; then
  echo "コンテナ '$POSTGRES_CONTAINER_NAME' がありません。先に just deps-up（または deps-up-prod）を実行してください。" >&2
  exit 1
fi

if [[ "$MODE" == "psql" ]]; then
  podman exec -it "$POSTGRES_CONTAINER_NAME" psql -U dev_user -d equipment_reservation
else
  podman exec -it "$POSTGRES_CONTAINER_NAME" bash
fi
