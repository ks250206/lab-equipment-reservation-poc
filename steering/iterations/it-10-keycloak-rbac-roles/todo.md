# TODO — it-10-keycloak-rbac-roles

- [x] ロール設計: レルムロール `app-admin`（`KEYCLOAK_APP_ADMIN_REALM_ROLE` で変更可）
- [x] FastAPI: `realm_access.roles` から `require_admin` を判定、`get_token_payload` を追加
- [x] `GET /api/users/me` の `role` を JWT 由来に統一
- [x] `PUT /api/users/{id}` から `role` 更新を除去（`UserUpdate` / サービス）
- [x] 開発シード: `ensure_keycloak_app_admin_realm_role` でロール作成・ユーザー割当
- [x] `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES` と DB ブートストラップを撤去
- [x] フロント: 管理者画面からロール編集を除去、文言を Keycloak ベースに更新
- [x] テスト・`doc/` / `.env.example` 更新
