#!/usr/bin/env bash
# ルートの docker-compose.yml を Podman または Docker で実行する。
# 既定: Podman（podman-compose）。Docker に切り替える場合は
#   export DEV_CONTAINER_RUNTIME=docker
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUNTIME="${DEV_CONTAINER_RUNTIME:-podman}"
FILE="${COMPOSE_FILE:-docker-compose.yml}"

run_docker() {
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$FILE" "$@"
  elif docker compose version >/dev/null 2>&1; then
    docker compose -f "$FILE" "$@"
  else
    echo "docker-compose または「docker compose」（Compose V2 プラグイン）が必要です。" >&2
    exit 1
  fi
}

case "$RUNTIME" in
  docker) run_docker "$@" ;;
  podman)
    if command -v podman-compose >/dev/null 2>&1; then
      podman-compose -f "$FILE" "$@"
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
