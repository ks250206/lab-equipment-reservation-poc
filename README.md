# 研究室装置予約システム PoC

研究室装置の予約・管理システム。

**前提**: 開発・検証の標準手順は **Nix flake の devShell**（`nix develop`）と **ルートの [Justfile](Justfile)**（`just`）です。ツールチェーンは [flake.nix](flake.nix) に集約しています。

## ドキュメント

| 種別 | パス |
|------|------|
| AI 向け必須ルール | [AGENTS.md](AGENTS.md) |
| ローカル開発（Compose・シード・トラブルシュート） | [doc/local-development.md](doc/local-development.md) |
| 本番運用の指針（環境変数・検証・注意点） | [doc/production-operations.md](doc/production-operations.md) |
| Keycloak クライアント（手動・補足） | [doc/keycloak-setup.md](doc/keycloak-setup.md) |
| 設計・アーキテクチャ等 | [doc/](doc/)（例: [doc/functional-design.md](doc/functional-design.md)） |
| リポジトリ構成の詳細 | [doc/repository-structure.md](doc/repository-structure.md) |

## 技術スタック（概要）

- **Backend**: Python 3.13, FastAPI, PostgreSQL, Keycloak (JWT), MinIO（S3 互換・装置画像）
- **Frontend**: React 19, Vite, Tailwind CSS, Radix UI（primitives）, TanStack Query
- **Dev**: Nix (flake), pnpm, uv, Podman（`just deps-*` 既定）または Docker

## クイックスタート（最短）

リポジトリルートで:

```bash
nix develop
just setup
just deps-up
just seed-dev          # 任意: DB + Keycloak クライアントの開発用投入（ENVIRONMENT=development のみ）
```

別ターミナル（どちらも `nix develop` 済みシェルで可）:

```bash
just backend-dev       # API: http://localhost:8000
just frontend-dev      # UI: http://localhost:5173
```

- コンテナ停止: `just deps-down`
- レシピ一覧: `just` または `just --list`
- **Podman 以外**: 依存起動の**前**に `export DEV_CONTAINER_RUNTIME=docker`

詳細（本番相当スタック、永続化、`just` を使わない手順など）は **[doc/local-development.md](doc/local-development.md)** を参照。

## よく使う `just`

| 用途 | コマンド |
|------|----------|
| 初回のツール・依存インストール | `just setup` |
| Postgres + Keycloak（開発プロファイル） | `just deps-up` / `just deps-down` |
| Postgres + Keycloak（本番相当・ローカル検証） | `just deps-up-prod` / `just deps-down-prod` |
| API / フロント開発サーバ | `just backend-dev` / `just frontend-dev` |
| 開発シード（DB + Keycloak API 可ならクライアント） | `just seed-dev` |
| 本番モード API / フロント静的プレビュー | `just backend-run-prod` / `just frontend-build` → `just frontend-preview` |
| Lint / テスト一式 | `just check` |

## 本番運用

クラウドへの具体的なデプロイ YAML はリポジトリ外とし、**揃える環境変数・TLS・Keycloak・DB バックアップ・デプロイ後チェック**を **[doc/production-operations.md](doc/production-operations.md)** に整理しています。

## 環境変数

| 場所 | 用途 |
|------|------|
| [.env.example](.env.example) | バックエンド・Compose 切替（`PERSISTENCE_PROFILE` 等） |
| [frontend/.env.example](frontend/.env.example) | フロント（`VITE_KEYCLOAK_*` 等） |

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

## トラブル（一例）

API が **ポート 8000 使用中**で起動しない → `just backend-free-port` または [doc/local-development.md](doc/local-development.md) の「ポート 8000」節。

Podman で **`just deps-up` が container_name 変更後に失敗**する → `just deps-reset-podman` のあと再度 `just deps-up`（詳細は [doc/local-development.md](doc/local-development.md) の該当節）。

## ディレクトリ構成（抜粋）

```
lab-equipment-reservation-poc/
├── doc/                 # 設計・開発・本番運用ドキュメント
├── Justfile             # just（Nix devShell 内で利用）
├── flake.nix            # Nix 開発環境
├── compose.yml          # Postgres（共通）
├── compose.dev.yml      # + Keycloak 開発
├── compose.prod.yml     # + Keycloak 本番相当（Postgres JDBC）
├── scripts/compose.sh   # Podman/Docker + プロファイル選択
├── backend/             # FastAPI
└── frontend/            # React + Vite
```
