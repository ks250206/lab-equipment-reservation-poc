# 研究室装置予約 PoC — タスクランナー
# `just` は flake の devShell に含める（`nix develop` 後に利用可能）。
#
# 依存コンテナ（PostgreSQL / Keycloak）: scripts/compose.sh（Podman 既定）
#   DEV_CONTAINER_RUNTIME=docker … Docker 系
#   PERSISTENCE_PROFILE=development（既定）| production … compose 重ね合わせ
#     development: Keycloak dev-file をボリューム keycloak_dev_data に永続化
# 本番相当: `just deps-up-prod` 等（prod グループ）。アプリは ENVIRONMENT=production で起動。

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# リポジトリルート（just は Justfile があるディレクトリで実行される想定）
root := justfile_directory()

default:
	@just --list

# --- 依存サービス（compose.yml） ---

[group('deps')]
deps-up:
	bash "{{root}}/scripts/compose.sh" up -d

# deps-down: 既定はコンテナのみ。永続削除は `just deps-down volumes`（compose down -v）
[group('deps')]
deps-down volumes="":
	#!/usr/bin/env bash
	args=(down)
	if [[ -n "{{volumes}}" ]]; then
	  if [[ "{{volumes}}" != "volumes" ]]; then
	    echo "不明な引数: '{{volumes}}'（ボリューム削除は: just deps-down volumes）" >&2
	    exit 1
	  fi
	  args+=(-v)
	fi
	bash "{{root}}/scripts/compose.sh" "${args[@]}"

# Podman のみ: container_name 変更後など compose が不整合なとき、旧コンテナと既定ネットを掃除してから deps-up しやすくする
[group('deps')]
deps-reset-podman:
	bash "{{root}}/scripts/deps_reset_podman.sh"

[group('deps')]
deps-ps:
	bash "{{root}}/scripts/compose.sh" ps

[group('deps')]
deps-logs *args:
	bash "{{root}}/scripts/compose.sh" logs {{args}}

# 開発スタックの Postgres コンテナで対話 psql（要: just deps-up 済み）
# Podman: podman-compose exec は -it 非対応のため scripts/postgres_interactive.sh 経由
[group('deps')]
deps-psql:
	bash "{{root}}/scripts/postgres_interactive.sh" psql

# 同上コンテナに bash で入る（手動で psql する場合）
[group('deps')]
deps-postgres-shell:
	bash "{{root}}/scripts/postgres_interactive.sh" shell

# --- 本番相当（compose: Keycloak→Postgres / アプリは本番モード） ---

[group('prod')]
deps-up-prod:
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/compose.sh" up -d

# deps-down-prod: 同上。ボリューム削除は `just deps-down-prod volumes`
[group('prod')]
deps-down-prod volumes="":
	#!/usr/bin/env bash
	args=(down)
	if [[ -n "{{volumes}}" ]]; then
	  if [[ "{{volumes}}" != "volumes" ]]; then
	    echo "不明な引数: '{{volumes}}'（ボリューム削除は: just deps-down-prod volumes）" >&2
	    exit 1
	  fi
	  args+=(-v)
	fi
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/compose.sh" "${args[@]}"

[group('prod')]
deps-ps-prod:
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/compose.sh" ps

[group('prod')]
deps-logs-prod *args:
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/compose.sh" logs {{args}}

[group('prod')]
deps-psql-prod:
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/postgres_interactive.sh" psql

[group('prod')]
deps-postgres-shell-prod:
	PERSISTENCE_PROFILE=production bash "{{root}}/scripts/postgres_interactive.sh" shell

[group('prod')]
backend-run-prod:
	cd "{{root}}/backend" && ENVIRONMENT=production uv run fastapi run

[group('prod')]
frontend-preview:
	cd "{{root}}/frontend" && pnpm run preview

# --- 初回セットアップ ---

[group('setup')]
setup-env:
	#!/usr/bin/env bash
	cd "{{root}}"
	test -f .env || cp .env.example .env
	test -f frontend/.env || cp frontend/.env.example frontend/.env
	echo "Ensured .env and frontend/.env (copy from .example if missing)."

[group('setup')]
backend-sync:
	cd "{{root}}/backend" && uv sync

[group('setup')]
frontend-install:
	cd "{{root}}/frontend" && pnpm install

[group('setup')]
setup: setup-env backend-sync frontend-install
	@echo "Setup done. Next: just deps-up  then  just backend-dev / just frontend-dev"

# --- アプリ開発サーバ ---
# ポート: FastAPI CLI は環境変数 PORT を参照（未設定時は 8000）。
# 取り残しプロセスで 8000 が塞がる場合は `just backend-free-port` のあと再起動。

[group('dev')]
backend-free-port:
	#!/usr/bin/env bash
	pids="$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)"
	if [[ -z "$pids" ]]; then
	  echo "Port 8000: no LISTEN processes found."
	  exit 0
	fi
	echo "Port 8000: stopping PIDs: $pids"
	kill $pids 2>/dev/null || true
	sleep 0.5
	if lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
	  echo "Still busy; try: kill -9 $pids" >&2
	  exit 1
	fi
	echo "Port 8000 is free."

[group('dev')]
backend-dev:
	cd "{{root}}/backend" && uv run fastapi dev

# Keycloak にダミー利用者を冪等作成 → users に sub 同期 → devices 投入 → Admin API で SPA クライアント等（要: Keycloak 起動済み）
[group('dev')]
seed-dev:
	cd "{{root}}/backend" && PYTHONPATH=src uv run python -m app.seeding

[group('dev')]
frontend-dev:
	cd "{{root}}/frontend" && pnpm dev

# --- 品質チェック（イテレーション完了時のループ用） ---

[group('check')]
backend-fmt:
	cd "{{root}}/backend" && uv run ruff format src tests

[group('check')]
backend-lint:
	cd "{{root}}/backend" && uv run ruff check src tests

[group('check')]
backend-ty:
	cd "{{root}}/backend" && uv run ty check src/

[group('check')]
backend-test:
	cd "{{root}}/backend" && uv run --extra test pytest tests/

[group('check')]
backend-check: backend-fmt backend-lint backend-test backend-ty

[group('check')]
frontend-fmt:
	cd "{{root}}/frontend" && pnpm run format

[group('check')]
frontend-lint:
	cd "{{root}}/frontend" && pnpm run lint

[group('check')]
frontend-test:
	cd "{{root}}/frontend" && pnpm run test --run

[group('check')]
frontend-build:
	cd "{{root}}/frontend" && pnpm run build

[group('check')]
frontend-check: frontend-fmt frontend-lint frontend-test frontend-build

[group('check')]
check: backend-check frontend-check
