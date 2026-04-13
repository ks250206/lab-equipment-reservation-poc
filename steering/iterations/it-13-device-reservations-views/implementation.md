# 実装内容（イテレーション 13 — 装置ページの予約一覧・カレンダー）

## スコープ

- **API**: `GET /api/devices/{device_id}/reservations`（ログイン必須）。`from` / `to` 省略時は現在 UTC 前後 6 ヶ月。`include_cancelled` でキャンセル行を含められる。
- **サービス**: 装置 ID・時刻窓・キャンセル除外で予約を取得し `start_time` 昇順。
- **フロント**: 装置詳細に表示モード（リスト / 月 / 週 / 日）。FullCalendar で週・日・月、リストはテーブル。未ログイン時は案内のみ。
- **ドキュメント**: `doc/functional-design.md` の予約 API 表を更新。

## 非目標

- 装置ページからの予約作成・ドラッグ編集。
- 予約者名の Keycloak 解決。
