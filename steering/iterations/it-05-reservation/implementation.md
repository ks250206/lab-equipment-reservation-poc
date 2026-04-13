# 実装内容（イテレーション 5 — 予約）

## スコープ

- **`/api/reservations`** 配下の **予約 API**: 一覧（ログインユーザー自身）、作成、更新、削除。
- **ビジネスルール**: 同一装置で `cancelled` 以外の予約同士の時間帯重複を拒否。区間の前後関係を検証。`DELETE` は **204 No Content**。
- **作成ペイロード**から `user_id` を除外（JWT からバインド）。
- **サービス補助**: `check_time_overlap`、`services/reservations.py` での永続化。ルータ側のバリデーションをサービスと整合。
- **テスト**: サービス単体と `tests/test_reservations_api.py`（依存関係オーバーライド付き ASGI クライアント）。
