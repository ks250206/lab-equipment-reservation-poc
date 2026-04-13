# ローカル開発（Nix + just）

このドキュメントは **flake の devShell** と **ルートの Justfile** を前提にした、日常の開発・検証手順をまとめたものです（[README.md](../README.md) から詳細を分離）。

## 前提

- **Nix**: `nix develop` で `just` / `uv` / `pnpm` / `podman-compose` 等が入る（[flake.nix](../flake.nix)）。
- **コンテナ**: 既定は **Podman**。Docker のみ使う場合は、**依存起動の前**に `export DEV_CONTAINER_RUNTIME=docker`。
- **Compose**: [compose.yml](../compose.yml) をベースに、[compose.dev.yml](../compose.dev.yml)（開発）または [compose.prod.yml](../compose.prod.yml)（本番相当）を重ねる。選択は `PERSISTENCE_PROFILE` と [scripts/compose.sh](../scripts/compose.sh)（`just deps-up` / `just deps-up-prod` がラップ）。

## 初回セットアップ

リポジトリルートで:

1. `nix develop`
2. `just setup` … `.env` / `frontend/.env` の雛形、`uv sync`、`pnpm install`
3. `.env` と `frontend/.env` を必要なら編集（[.env.example](../.env.example)、[frontend/.env.example](../frontend/.env.example)）
4. `just deps-up` … Postgres + Keycloak（開発プロファイル）
5. `just seed-dev` … `ENVIRONMENT=development` のときのみ。DB に装置・ダミーユーザ、Keycloak が起動していれば `device-reservation` クライアントを Admin API で冪等更新（[keycloak-setup.md](keycloak-setup.md) 参照）
6. 別ターミナルで `just backend-dev` と `just frontend-dev`

ブラウザ: **http://localhost:5173** 。API ドキュメント: **http://localhost:8000/docs**。

終了: 各 dev サーバで `Ctrl+C` のあと、コンテナを止めるなら `just deps-down`。

## 2 回目以降

```bash
cd personal_space
nix develop
just deps-up          # 止めていたら
just backend-dev      # 別ターミナル
just frontend-dev     # 別ターミナル
```

シードだけやり直す: `just seed-dev`（冪等）。

## `just` 早見表

一覧は `just` または `just --list`（`[deps]` / `[dev]` / `[prod]` / `[check]` など）。

| 用途 | コマンド |
|------|----------|
| 初回準備 | `just setup` |
| 依存起動 / 停止（開発） | `just deps-up` / `just deps-down` |
| 本番相当の依存起動 / 停止 | `just deps-up-prod` / `just deps-down-prod` |
| ログ | `just deps-logs` / `just deps-logs-prod`（`-f` 等は compose にそのまま渡す） |
| API / フロント開発 | `just backend-dev` / `just frontend-dev` |
| 開発シード | `just seed-dev` |
| ポート 8000 掃除 | `just backend-free-port` |
| 品質 | `just backend-check` / `just frontend-check` / `just check` |
| 本番相当 API / 静的プレビュー | `just backend-run-prod` / `just frontend-build` → `just frontend-preview` |

`just backend-check` の `pytest` は **Postgres が起動済み**で `.env` の `DATABASE_URL` が妥当であることを前提とする。

## 本番相当スタック（ローカル検証）

開発の `just deps-up` と **同時起動しない**こと。切替前に `just deps-down` 推奨。

1. `just deps-up-prod` … Keycloak を Postgres の `keycloak` DB に接続
2. `.env` を接続先に合わせる（`DATABASE_URL`、JWT / Keycloak URL）
3. `just backend-run-prod` … `ENVIRONMENT=production` で `fastapi run`
4. `just frontend-build` のあと `just frontend-preview`

Postgres ボリュームが既にあり **`keycloak` DB が無い**と Keycloak が落ちることがある → 上記「永続化プロファイル」および [docker/postgres/init/01-keycloak.sql](../docker/postgres/init/01-keycloak.sql) を参照。

## 永続化プロファイル（要約）

| レイヤー | 開発（既定） | 本番相当（`just deps-up-prod`） |
|----------|--------------|----------------------------------|
| アプリ DB | `compose.yml` の Postgres（`postgres_data`） | 接続先は `.env` の `DATABASE_URL`（同一コンテナでも可） |
| Keycloak | dev-file + ボリューム `keycloak_dev_data` | Postgres 内 `keycloak` DB（`postgres_data`） |

dev と prod 相当で Keycloak の実体が **別**のため、レルム設定は自動では引き継がれない。開発用 KC データだけ消す: `just deps-down` 後に `docker volume rm` / `podman volume rm` で `keycloak_dev_data` を削除（名前は `docker volume ls` で確認）。

## サービス URL（ローカル既定）

| サービス | URL |
|----------|-----|
| Vite | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| Keycloak | http://localhost:8080 |
| Postgres | localhost:5432（`compose.yml` のユーザー参照） |

## ポート 8000 が使用中

1. `lsof -nP -iTCP:8000 -sTCP:LISTEN`
2. `Ctrl+C` または `just backend-free-port`
3. 別ポート: `PORT=8001 just backend-dev`（Vite プロキシの `target` も合わせる）

## Keycloak クライアント（手動）

自動シードで足りない場合や本番レルムでは [keycloak-setup.md](keycloak-setup.md)。

## `just` を使わない場合

```bash
bash scripts/compose.sh up -d
# 本番相当: PERSISTENCE_PROFILE=production bash scripts/compose.sh up -d
```

Docker 利用時は上記の **前**に `export DEV_CONTAINER_RUNTIME=docker`。

```bash
cd backend && uv sync && uv run fastapi dev
cd frontend && pnpm install && pnpm dev
```

エントリポイントは `backend/pyproject.toml` の `[tool.fastapi]`。
