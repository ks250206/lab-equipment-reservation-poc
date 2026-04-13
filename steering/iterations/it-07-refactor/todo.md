# TODO — it-07-refactor（リファクタリング）

- [x] バックエンド: `ruff` / `pytest` / `ty check` をイテレーション完了条件でグリーン維持
- [x] フロント: `oxlint` / `vitest` / `pnpm run build`（`tsc --noEmit` は build 内）
- [ ] 500 行超ファイルの分割検討（現状、分割は未実施）
- [ ] カバレッジ 80% 目標（`pytest-cov` で全体約 77%。主に `auth`・HTTP ルータ未カバー）
- [x] README に OpenAPI URL を追記
- [ ] （任意）手動 E2E の確認
