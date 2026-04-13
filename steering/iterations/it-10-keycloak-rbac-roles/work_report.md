# Work report — it-10-keycloak-rbac-roles

- 2026-04-14: steering 作成。
- 2026-04-14: `get_token_payload` / `require_admin` を JWT レルムロール判定に変更。`users/me` の `role` をトークン由来に。シードで `app-admin` 付与。ブートストラップ環境変数を撤去。結合テストは `get_token_payload` をオーバーライド。
