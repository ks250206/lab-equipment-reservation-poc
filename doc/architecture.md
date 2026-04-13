# 技術仕様書（アーキテクチャ）

テクノロジースタック、開発手法、制約、非機能要件の SSOT。

---

## 1. テクノロジースタック

| レイヤー | 技術 | バージョン目安 |
|---------|------|----------------|
| Python ランタイム | CPython + uv | 3.13 |
| 静的解析 | ty, ruff | プロジェクト指定に従う |
| Web API | FastAPI + Pydantic | プロジェクト依存に従う |
| DB | PostgreSQL + asyncpg + SQLAlchemy | PostgreSQL 16 系 |
| フロント | React + Vite | React 19, Vite 6 |
| パッケージ | pnpm | 9 |
| Node | LTS | v24.14.1 目安 |
| テスト | pytest（Python）, vitest（React） | プロジェクト依存に従う |
| 認証 | Keycloak | 26 |

## 2. 開発ツールと手法

- **Python**: `uv` で依存管理・実行。`ruff` で lint / format。`ty check src/` で型チェック（厳密モードを前提とする）。
- **TypeScript**: `tsc --noEmit`、`oxlint`、`oxfmt`。
- **コンテナ**: 開発の既定は **Podman**（`podman-compose`）。Docker 利用時は `DEV_CONTAINER_RUNTIME=docker` で Keycloak と PostgreSQL を起動。
- **永続化プロファイル**: `PERSISTENCE_PROFILE=development|production` で Compose の重ね方を切替（[doc/local-development.md](local-development.md)）。開発では Keycloak が **dev-file**（H2 を **名前付きボリューム `keycloak_dev_data`** に保存しコンテナ再作成でも保持）、本番相当では Keycloak が **同一 Postgres 上の `keycloak` DB**（`postgres_data` ボリューム）に JDBC 接続する。
- **Nix**: `flake.nix` による開発シェル（任意だがリポジトリの推奨環境）。シェルに **`just`** を含め、ルート [Justfile](../Justfile) で依存起動・開発・品質チェックを統一する（一覧は [@doc/development-guidelines.md](development-guidelines.md) 5.2）。

## 3. 技術的制約と要件

- DB アクセスは **非同期**（asyncpg + SQLAlchemy asyncio）を用いる。
- 認証は **JWT（RS256）** を前提とし、オーディエンス・issuer を設定に合わせて検証する。
- テスト方針（モック禁止など）は [@doc/development-guidelines.md](development-guidelines.md)。

## 4. パフォーマンス要件（PoC）

- 明示的な数値 SLA は定めない。
- 装置検索はインクリメンタル（ファセット）であり、不必要な全件ロードを避ける設計とする。
- 本番負荷試験は PoC 範囲外。

## 5. フロントエンドと認証の連携方針

- 開発時は Keycloak のクライアント設定で Vite のオリジンを許可する。
- トークン保管方式（例: `localStorage`）はセキュリティトレードオフを理解したうえで実装し、本番移行時に見直す。
- **利用者データの二層**: 認証の正は Keycloak。アプリ用 `users` 行は JWT の `sub` に紐づけて初回 API アクセス時に作成し、予約 FK や表示用プロフィールに使う（詳細は [@doc/functional-design.md](functional-design.md) の users 節）。**認可（管理者など）**はイテレーション 10 以降、Keycloak のロールクレームを正とする予定（現状は DB `role` 依存）。

## 6. 設定・秘密情報

- 接続文字列やクライアント秘密は `.env` に置き、リポジトリにコミットしない。テンプレートは `.env.example` を正とする。
