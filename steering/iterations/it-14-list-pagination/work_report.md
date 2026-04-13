# it-14 作業メモ

- 装置一覧は `search_devices_paginated`、装置予約は `list_reservations_for_device_in_window_paginated` で件数＋ `offset/limit` を同一条件で取得。
- シード予約は `run_seed` 内で装置 upsert 後に `Reservation` をバッチ追加。再実行時は既存の `Reservation` 削除ロジックで除去される。
