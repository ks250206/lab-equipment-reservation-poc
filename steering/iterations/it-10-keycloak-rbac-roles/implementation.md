# 実装内容（イテレーション 10 — Keycloak RBAC とアプリロール）

## 実装済み

- **認可**: `require_admin` は JWT の `realm_access.roles` に `settings.keycloak_app_admin_realm_role`（既定 **`app-admin`**）があるかで判定。API の認可には `users.role` を使わない。
- **依存関係**: `get_token_payload` で Bearer をリクエストあたり一度だけデコード。`get_current_user` はそれを基盤にする。管理者フローを実 JWT なしで試すテストでは `get_token_payload` をオーバーライド。
- **`GET /api/users/me`**: `UserResponse` の `role` はトークン由来（`admin` / `user`）。DB 列は参照しない。
- **`PUT /api/users/{id}`**: `UserUpdate` は **`name` のみ**。ロール変更は Keycloak 側で行う。
- **ユーザー作成**: 新規 DB 行のレガシー列 `role` は常に `user`。
- **Keycloak シード**（`ensure_keycloak_app_admin_realm_role`）: レルムロールの冪等作成と `KEYCLOAK_SEED_GRANT_APP_ADMIN_USERNAME`（既定 `admin`）への付与。SPA クライアントシード後に `just seed-dev` から呼び出し。
- **削除**: `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES` と `auth.py` の preferred-username ブートストラップ。
- **フロント**: 管理者のユーザーページは表示名のみ編集。Keycloak の `app-admin` と、一覧の `role` が DB のみである旨の文言。
- **ドキュメント**: `doc/functional-design.md`、`doc/architecture.md`、`doc/keycloak-setup.md`、`.env.example` を上記に整合。

## 非目標（変更なし）

- Keycloak 管理コンソールの完全代替、管理者／一般ユーザー以外の細かい ACL、PoC 既定を超えるマルチレルム対応。

## 補足（後続イテレーション）

- **it-11** で `users` テーブルから `email` / `name` / `role` 列を削除し、`PUT /api/users/{id}` を廃止した（本ファイルの「`PUT`」「`users.role`」は it-10 時点の記述として残す）。
