# TODO — it-10-keycloak-rbac-roles

- [ ] ロール設計を確定する（レルムロール vs `device-reservation` クライアントロール、ロール名、composite の要否）
- [ ] FastAPI: JWT からロールを抽出するモジュール（`decode_token` 後のクレーム解釈）と `require_admin` の置き換え
- [ ] `GET /api/users/me` の `role` を Keycloak 由来に統一（必要なら DB 列の扱いを決めてマイグレーション or 無視化）
- [ ] `PUT /api/users/{id}` の `role` 更新の扱い（削除・Keycloak Admin API 連携・403 等）を仕様どおりに変更
- [ ] 開発シード: Keycloak Admin API でロール作成・ユーザー割当を冪等に追加（`keycloak_seed.py` 拡張など）
- [ ] `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES` および dev 専用の `admin` 自動昇格ロジックを撤去または無効化し、`.env.example` / `doc/` を追随
- [ ] フロント: 管理者画面の表示条件をトークンまたは更新後の `/users/me` に合わせる
- [ ] テスト・`ty` / `ruff` / pytest をグリーンにし、`work_report.md` を更新
