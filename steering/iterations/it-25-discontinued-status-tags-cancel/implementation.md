# 実装内容（イテレーション 25 — discontinued・タグ・キャンセル表示・論理削除）

## スコープ

- `DeviceStatus.DISCONTINUED` とシード（装置・予約の `cancelled` / `completed` 混在）。
- 装置予約 API: リストは本人のキャンセルのみ他人キャンセル除外、`calendar_mode` でカレンダーはキャンセル常時除外。
- `DELETE /api/reservations/{id}` を確定行の論理キャンセル（`cancelled`）に変更。
- フロント: `DeviceStatusTag` / `ReservationStatusTag`、予約一覧のキャンセルは `Ban` + `PUT`。

## 非目標

- Alembic 導入や本番 DB の自動マイグレーション。

## 補足

- 既存 Postgres の ENUM 拡張は `doc/local-development.md` に手動手順を記載。
