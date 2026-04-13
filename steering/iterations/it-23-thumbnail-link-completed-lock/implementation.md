# it-23: サムネ画像リンク・完了予約の削除／更新禁止

## フロント

- `DeviceImageSlot` に任意の `to`（React Router のパス）。装置一覧の **サムネ・詳細**モードで `/devices/{id}` を指定。
- 予約一覧: **`status === "completed"`** の行は **削除**を `disabled` + `title`。
- `ReservationDetailDialog`: 完了済みは **閲覧のみ**（保存ボタンなし、説明文で案内）。

## バックエンド

- `DELETE /api/reservations/{id}`: 対象が **`completed`** なら **409**（`delete_reservation` サービスで検証しルータから呼び出し）。
- `PUT /api/reservations/{id}`: 既存行が **`completed`** なら **409**（ステータスを戻してから削除する抜け道を防ぐ）。

## テスト

- `test_reservations_api`: DELETE / PUT が 409。
- `test_services`: `delete_reservation` が `ValueError`。
