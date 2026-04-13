# 室内装置予約 PoC — タスクランナー
# `just` は flake の devShell に含める（`nix develop` 後に利用可能）。
#
# 依存コンテナ（PostgreSQL / Keycloak）:
#   既定は Docker Compose v2（`docker compose`）。Podman の場合は
#   `export DEV_CONTAINER_RUNTIME=podman` してから `just deps-up` 等を実行。

set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# リポジトリルート（just は Justfile があるディレクトリで実行される想定）
root := justfile_directory()

default:
	@just --list

# --- 依存サービス（docker-compose.yml） ---

[group('deps')]
deps-up:
	#!/usr/bin/env bash
	cd "{{root}}"
	case "${DEV_CONTAINER_RUNTIME:-docker}" in
	  docker) docker compose -f docker-compose.yml up -d ;;
	  podman) podman-compose -f docker-compose.yml up -d ;;
	  *) echo "DEV_CONTAINER_RUNTIME must be docker or podman"; exit 1 ;;
	esac

[group('deps')]
deps-down:
	#!/usr/bin/env bash
	cd "{{root}}"
	case "${DEV_CONTAINER_RUNTIME:-docker}" in
	  docker) docker compose -f docker-compose.yml down ;;
	  podman) podman-compose -f docker-compose.yml down ;;
	  *) echo "DEV_CONTAINER_RUNTIME must be docker or podman"; exit 1 ;;
	esac

[group('deps')]
deps-ps:
	#!/usr/bin/env bash
	cd "{{root}}"
	case "${DEV_CONTAINER_RUNTIME:-docker}" in
	  docker) docker compose -f docker-compose.yml ps ;;
	  podman) podman-compose -f docker-compose.yml ps ;;
	  *) echo "DEV_CONTAINER_RUNTIME must be docker or podman"; exit 1 ;;
	esac

[group('deps')]
deps-logs *args:
	#!/usr/bin/env bash
	cd "{{root}}"
	case "${DEV_CONTAINER_RUNTIME:-docker}" in
	  docker) docker compose -f docker-compose.yml logs {{args}} ;;
	  podman) podman-compose -f docker-compose.yml logs {{args}} ;;
	  *) echo "DEV_CONTAINER_RUNTIME must be docker or podman"; exit 1 ;;
	esac

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
