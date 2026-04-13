# 実装内容（イテレーション 11 — users テーブル縮小と Keycloak 正の明文化）

## スコープ

- **`users` テーブル**: `id`（UUID PK）、`keycloak_id`（UNIQUE）、`created_at` のみに縮小。`email` / `name` / `role` 列を削除（破壊的変更）。
- **認証**: `get_or_create_user_from_payload` は `keycloak_id` のみ INSERT。プロフィールは JWT／Keycloak を正とする。
- **API**: `GET /api/users/me` は `UserMeResponse`（DB 由来＋ JWT 由来の合成）。`GET /api/users`・`GET /api/users/{id}` は `UserResponse`（`id` / `keycloak_id` / `created_at` のみ）。`PUT /api/users/{id}` を削除。
- **シード**: ダミー `users` は `id` + `keycloak_id` のみで冪等 upsert。
- **フロント**: 管理者ユーザー一覧からメール・ロール列と編集 UI を削除。型を `/me` 用と一覧用に分離。
- **ドキュメント**: `doc/functional-design.md` ほか SSOT を縮小スキーマと手順（DB ボリューム再作成）に合わせて更新。

## 非目標

- Keycloak Admin API で一覧にメール・表示名を解決する。
- Alembic 等による本番向け列削除マイグレーション。

## 補足

- 既存 Postgres ボリュームは `create_all` では列削除されないため、`doc/local-development.md` に **ボリューム削除 → 依存再起動 → `just seed-dev`** を明記した。
