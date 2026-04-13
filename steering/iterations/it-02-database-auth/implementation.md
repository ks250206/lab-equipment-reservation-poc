# 実装内容（イテレーション 2 — データベースと認証）

## スコープ

- コアテーブル（`devices`、`users`、`reservations`）の **PostgreSQL** スキーマを SQLAlchemy 2.x 非同期モデルで定義。
- **Keycloak JWT** の検証（`python-jose`、JWKS）、現在ユーザーを返す FastAPI 依存関係と遅延 DB 同期。
- **ユーザー API**: `GET /api/users/me`、管理者限定の一覧・詳細エンドポイント。
- `routers/`、`services/`、`schemas/`、ORM `models/` へのプロジェクトレイアウト分割。
