# it-15: 予約リストのユーザー表示とシード日付の 2 か月分散

## 実装内容

- `users` に `email` / `name`（NULL 可）を追加。`init_db` で `ALTER TABLE ... IF NOT EXISTS` を実行。
- 開発シード・オフラインシードで `email` / `name` を投入。JWT 初回作成・NULL 補完で `get_or_create_user_from_payload` を拡張。
- `GET /api/devices/{id}/reservations` の `ReservationResponse` に `user_name` / `user_email` を付与（`selectinload(Reservation.user)`）。
- 予約シードは `build_reservation_seed_rows(at=...)` で、UTC の当月 1 日〜翌々月 1 日の半開区間に 1 時間枠を均等配置。
- フロント装置予約テーブルを「氏名」「メール」列に分割。
