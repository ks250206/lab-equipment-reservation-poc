# Implementation (Iteration 7 — Refactor & Polish)

## Done

- **タイムゾーン一貫性**: `DateTime(timezone=True)` と UTC 保存に合わせ、`ensure_utc`（`src/app/datetime_util.py`）をルータ・予約サービス・重複チェックで共有。naive を UTC として扱い、aware は UTC に正規化。
- **静的解析**: `python-jose` 例外参照の整理、`ty check` / `ruff` グリーン（`datetime.UTC` エイリアス準拠）。
- **テスト**: 予約・装置・スキーマ関連の `datetime` を UTC aware に統一。`test_datetime_util.py` で `ensure_utc` の分岐をカバー。
- **ドキュメント**: ルート `README` に Swagger UI URL を追記。

## Deferred / follow-up

- 行数ベースのモジュール分割は未着手（恩恵が小さい箇所は据え置き）。
- 全体カバレッジ 80% は、Keycloak 連携をモックなしで広く叩く必要があり、別イテレーションで HTTP 統合テスト設計が望ましい。
