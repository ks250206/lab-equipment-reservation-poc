# 実装内容（イテレーション 26 — 予約一覧キャンセル表示・トースト）

## スコープ

- `GET /api/reservations` の `include_cancelled` 既定を **`true`**。ステータス未指定時はキャンセル行も返す。`false` のときのみキャンセルを除外。
- フロントの URL 同期・`fetchReservations` を上記に合わせ、チェックボックスを **「キャンセル済みを一覧から隠す」**（`include_cancelled=false`）に変更。
- **Radix Toast** による `AppToastProvider`（`main.tsx` でラップ）。予約一覧のキャンセル・詳細ダイアログからのキャンセル・利用完了報告の成功時にスナックバー表示。

## 非目標

- トーストのキューイングや複数同時表示の高度な UX。
