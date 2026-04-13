# Work report — it-07-refactor

## 2026-04-13

- `datetime_util.ensure_utc` を導入し、予約 API・サービス・`check_time_overlap` で naive/aware 混在による DB エラーや重複判定のずれを防いだ。
- バックエンド: `ruff check` / `ruff format`、`pytest`（55 件）、`ty check src/` を通過。
- フロント: `pnpm run lint`、`vitest run`、`pnpm run build` を通過。
- `pytest-cov`（`src/app`）は約 77%。未達分は主に JWT 検証と FastAPI ルータ直叩きの欠如。
- README に `http://localhost:8000/docs` を追記。`AGENTS.md` のイテレーション7を完了に更新。
