# 室内装置予約 PoC — タスクランナー
# `just` は flake の devShell に含める（`nix develop` 後に利用可能）。
#
# 依存コンテナ（PostgreSQL / Keycloak）:
#   既定は Podman（`podman-compose`）。実体は scripts/compose.sh。
#   Docker に切り替える場合は `export DEV_CONTAINER_RUNTIME=docker`。

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# リポジトリルート（just は Justfile があるディレクトリで実行される想定）
root := justfile_directory()

default:
	@just --list

# --- 依存サービス（docker-compose.yml） ---

[group('deps')]
deps-up:
	bash "{{root}}/scripts/compose.sh" up -d

[group('deps')]
deps-down:
	bash "{{root}}/scripts/compose.sh" down

[group('deps')]
deps-ps:
	bash "{{root}}/scripts/compose.sh" ps

[group('deps')]
deps-logs *args:
	bash "{{root}}/scripts/compose.sh" logs {{args}}

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

[group('dev')]
backend-dev:
	cd "{{root}}/backend" && uv run fastapi dev

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
	cd "{{root}}/backend" && uv run pytest tests/

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
