# it-22: 装置お気に入り・一覧マイ向けフィルタ・装置予約リスト絞り込み・カレンダー色分け

## バックエンド

- テーブル `user_favorite_devices`（`UserFavoriteDevice`）：複合 PK `(user_id, device_id)`、CASCADE。
- `GET /api/devices`：`used_by_me` / `favorites_only`（要 Bearer）。未ログインで true → **400**。任意の Bearer で `is_favorite` を各 item に付与。
- `GET /api/devices/{id}`：任意 Bearer で `is_favorite`。
- `POST` / `DELETE /api/users/me/favorites/{device_id}`：**204**（冪等）。
- `GET /api/devices/{id}/reservations`：`mine_only` / `reservation_status`（`include_cancelled` より `reservation_status` を優先）。
- `get_optional_current_user`：`HTTPBearer(auto_error=False)`。

## フロント

- 装置一覧：予約由来フィルタを削除し、`used_by_me` / `favorites_only`（URL `used_by_me=1` 等）。`fetchDevices` にトークン付与。
- 装置詳細：お気に入りトグル、`fetchDevice` にトークン。
- 装置予約セクション：リスト用「すべて / 自分のみ」、ステータス select。
- FullCalendar：自分／他人で背景・枠線色を分離。

## テスト

- `test_devices_api.py`：個人フィルタ要ログイン、used / favorites / is_favorite。
- `test_device_reservations_api.py`：`mine_only` と `reservation_status`。
- Vitest：`reservationsToFullCalendarEvents` の色プロパティ。
