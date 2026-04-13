# Implementation (Iteration 7 — Refactor & Polish)

## Done

- **タイムゾーン一貫性**: `DateTime(timezone=True)` と UTC 保存に合わせ、`ensure_utc`（`src/app/datetime_util.py`）をルータ・予約サービス・重複チェックで共有。naive を UTC として扱い、aware は UTC に正規化。
- **静的解析**: `python-jose` 例外参照の整理、`ty check` / `ruff` グリーン（`datetime.UTC` エイリアス準拠）。
- **テスト**: 予約・装置・スキーマ関連の `datetime` を UTC aware に統一。`test_datetime_util.py` で `ensure_utc` の分岐をカバー。
- **ドキュメント**: ルート `README` に Swagger UI URL を追記。

## Follow-up (after initial it-07 pass)

- **テスト拡充**: `decode_token(..., jwks=...)` で JWT 検証を実キー検証。装置・ユーザー API を `AsyncClient` + 依存性オーバーライドで結合テスト化。予約 API の 404/400 系を追加。
- **HTTP**: 装置 `DELETE` を `204 No Content` に変更。
- **カバレッジ**: `src/app` 全体で **約 96%**（残りは主に `auth` の JWKS HTTP 取得と `get_current_user` のワイヤ部分、`db` / `main` のごく一部）。

## Deferred / follow-up

- 行数ベースのモジュール分割は未着手（バックエンドに 500 行超ファイルなし）。
- Keycloak 実サーバに繋ぐ E2E は任意（モック方針外のまま）。
