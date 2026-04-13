# TODO — it-07-refactor（リファクタリング）

- [x] バックエンド: `ruff` / `pytest` / `ty check` をイテレーション完了条件でグリーン維持
- [x] フロント: `oxlint` / `vitest` / `pnpm run build`
- [x] カバレッジ: `pytest-cov`（`src/app`）**約 96%**（Keycloak 実 JWKS 取得・`get_current_user` 直結合以外はカバー）
- [x] 装置 DELETE の HTTP ステータスを **204** に統一（予約 API と同様）
- [ ] 500 行超ファイルの分割（現状バックエンドに該当なし）
- [ ] （任意）Keycloak 起動下での `get_jwt_public_keys` / `get_current_user` E2E
