# 実装内容（イテレーション 9 — 永続化プロファイルと開発シード）

## スコープ

- **Compose 分割**: `compose.yml`（Postgres + init）+ `compose.dev.yml`（Keycloak `KC_DB=dev-file`）+ `compose.prod.yml`（Keycloak を `KC_DB=postgres` で共有 Postgres 上の DB `keycloak` に向ける）。`scripts/compose.sh` が `PERSISTENCE_PROFILE`（既定 `development`、JDBC スタックは `production`）でペアを選択。
- **Postgres init**: `docker/postgres/init/01-keycloak.sql` で Keycloak 用ロール／データベースを作成（初回ボリューム初期化時のみ実行）。
- **アプリ設定**: `ENVIRONMENT` / `APP_ENV`（`development` | `production`）を検証付きで定義。`Settings()` は `backend/` またはリポジトリルートの `.env` を読む（`env_file` タプル）。
- **開発シード**: `app.seeding` モジュール — 33 台の装置（11 ラボカテゴリ × 3）と 8 名の日本語ダミーユーザー（管理者 1 名）を冪等 upsert。`ENVIRONMENT=production` のときは実行しない。テスト用に `run_seed(session_factory=...)`。
- **Just**: `seed-dev` レシピ。`backend-test` は `uv run --extra test` で pytest を利用可能に。

## Keycloak とアプリ DB の関係

- **開発**: Keycloak のレルムデータは **dev-file** ストレージに置き、アプリの `equipment_reservation` データベースとは別。
- **本番プロファイル**: Keycloak はアプリと同一 Postgres サーバ上の **別データベース**（`keycloak`）を JDBC で利用。`equipment_reservation` スキーマとは独立。

## 非目標

- API 起動時の自動シードは行わない。
- Keycloak のレルム JSON インポートは行わない。SPA クライアント設定は手動（README）のまま。
