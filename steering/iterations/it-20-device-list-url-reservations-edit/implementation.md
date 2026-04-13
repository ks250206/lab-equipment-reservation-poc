# 実装内容（イテレーション 20 — 装置一覧 URL 同期・予約一覧のページング／フィルター／編集）

## スコープ

- 装置一覧（`/devices`）のフィルタ・ページ・表示モードをクエリ文字列と双方向同期（ブックマーク・戻る／進む対応）。
- `GET /api/reservations` をページング JSON に変更し、装置・ステータス・期間・キャンセル含有で絞り込み可能にした。
- 予約一覧ページにフィルター・ページネーション・行ごとの編集ダイアログ（既存 `ReservationDetailDialog`）を追加。
- 装置詳細の予約リストに右端の編集ボタン（Lucide `Pencil`）。カレンダーはイベント表示を氏名のみ、`title` 属性に時刻＋氏名。
- 共通: `ListPageSize` を `pagination.py`、`Reservation`→`ReservationResponse` を `reservation_mapping.py` に集約。

## 非目標

- 予約一覧の URL パラメータ名の国際化や短縮エイリアス。
- OpenAPI スキーマの手動再生成（FastAPI が `/docs` で反映）。

## 補足

- クエリ名 `status` は FastAPI の `fastapi.status` と衝突するため、ユーザー予約一覧のステータス絞り込みは **`reservation_status`** とした。
