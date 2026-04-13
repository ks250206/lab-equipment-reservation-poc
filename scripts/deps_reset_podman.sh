#!/usr/bin/env bash
# Podman で compose の container_name を変えたあと、旧コンテナ／ネットワークが残り
# `just deps-up` が失敗するときの救済用（開発プロファイル想定）。
#
# 使い方: リポジトリルートから
#   bash scripts/deps_reset_podman.sh
# または just deps-reset-podman
#
# 本番相当スタックを掃除する場合は先頭で PERSISTENCE_PROFILE=production を付ける。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUNTIME="${DEV_CONTAINER_RUNTIME:-podman}"
if [[ "$RUNTIME" != "podman" ]]; then
  echo "DEV_CONTAINER_RUNTIME が podman ではありません（現在: $RUNTIME）。このスクリプトは Podman 専用です。" >&2
  exit 1
fi

if ! command -v podman >/dev/null 2>&1; then
  echo "podman が見つかりません。" >&2
  exit 1
fi

echo "== compose down（失敗しても続行） =="
bash "$ROOT/scripts/compose.sh" down 2>/dev/null || true
if [[ "${PERSISTENCE_PROFILE:-development}" == production ]] || [[ "${PERSISTENCE_PROFILE:-}" == prod ]]; then
  PERSISTENCE_PROFILE=production bash "$ROOT/scripts/compose.sh" down 2>/dev/null || true
fi

# 新旧 container_name（compose で固定している名前）
STALE_CONTAINERS=(
  device-reservation-postgres
  device-reservation-keycloak
  device-reservation-minio
  equipment-reservation-postgres
  equipment-reservation-keycloak
  equipment-reservation-minio
)

echo "== 既知の名前のコンテナを強制削除 =="
for name in "${STALE_CONTAINERS[@]}"; do
  if podman inspect -t container "$name" >/dev/null 2>&1; then
    echo "  removing $name"
    podman rm -f "$name" || true
  fi
done

# Compose 既定のプロジェクト名はディレクトリ名（COMPOSE_PROJECT_NAME 未設定時）
PROJ="${COMPOSE_PROJECT_NAME:-$(basename "$ROOT")}"
NET_DEFAULT="${PROJ}_default"

echo "== 既定ブリッジネットワークの削除試行: $NET_DEFAULT =="
if podman network inspect "$NET_DEFAULT" >/dev/null 2>&1; then
  podman network rm -f "$NET_DEFAULT" || echo "  （ネットワークはまだ使用中のため手動確認: podman network inspect $NET_DEFAULT）"
else
  echo "  （ネットワーク $NET_DEFAULT は存在しません）"
fi

echo "== 完了。続けて just deps-up を実行してください。 =="
echo "Podman が \"proxy already running\" で失敗する場合: podman machine stop && podman machine start"
