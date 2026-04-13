#!/usr/bin/env bash
# ルートの Compose ファイル（compose.yml 系）を Podman または Docker で実行する。
# 既定: Podman。永続プロファイル:
#   PERSISTENCE_PROFILE=development（既定）→ compose.yml + compose.dev.yml
#       Keycloak: dev-file + 名前付きボリューム keycloak_dev_data（コンテナ再起動でも保持）
#   PERSISTENCE_PROFILE=production          → compose.yml + compose.prod.yml
#       Keycloak: Postgres の keycloak DB（postgres_data ボリューム内）
# Docker に切り替える場合は export DEV_CONTAINER_RUNTIME=docker
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUNTIME="${DEV_CONTAINER_RUNTIME:-podman}"
PROFILE_RAW="${PERSISTENCE_PROFILE:-development}"
PROFILE="$(printf '%s' "$PROFILE_RAW" | tr '[:upper:]' '[:lower:]')"

case "$PROFILE" in
  production | prod)
    compose_files=( -f "$ROOT/compose.yml" -f "$ROOT/compose.prod.yml" )
    ;;
  development | dev | *)
    compose_files=( -f "$ROOT/compose.yml" -f "$ROOT/compose.dev.yml" )
    ;;
esac

run_docker() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "${compose_files[@]}" "$@"
  elif docker compose version >/dev/null 2>&1; then
    docker compose "${compose_files[@]}" "$@"
  else
    echo "docker-compose または「docker compose」（Compose V2 プラグイン）が必要です。" >&2
    exit 1
  fi
}

case "$RUNTIME" in
  docker) run_docker "$@" ;;
  podman)
    if command -v podman-compose >/dev/null 2>&1; then
      podman-compose "${compose_files[@]}" "$@"
    else
      echo "podman-compose が見つかりません（nix develop では flake に含まれています）。" >&2
      exit 1
    fi
    ;;
  *)
    echo "DEV_CONTAINER_RUNTIME は docker または podman です（現在: $RUNTIME）。" >&2
    exit 1
    ;;
esac
