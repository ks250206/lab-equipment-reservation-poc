# 実装内容（イテレーション 24 — 予約 UX・完了フロー）

## スコープ

- 予約の時間重複エラーを **日本語 `detail`** とし、フロントは **`messageFromApiErrorBody`** で JSON エラーを整形表示する。
- `GET /api/reservations` に **`favorites_only`** を追加し、予約一覧 URL と同期する。
- **`POST /api/reservations/{id}/complete-usage`** で確定予約のみ `completed` へ。`PUT` で `completed` への変更は **常に 409**。
- 予約一覧から新規作成 UI を削除し、**`/reservations/usage-complete`** で利用完了報告を行う。`App` / `Layout` にルート・ナビを追加。

## 非目標

- Keycloak や MinIO の設定変更。
- 管理者向け予約の一括操作。

## 補足

- 仕様の SSOT は `doc/functional-design.md` の該当節を更新済み。
