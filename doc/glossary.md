# ユビキタス言語定義

ドメイン・UI・コード上の用語の SSOT。

---

## 1. ドメイン用語

| 用語（日本語） | 英語・コード上の対応 | 定義 |
|----------------|---------------------|------|
| 装置 | Device | 予約の対象となる室内機器・設備 |
| 予約 | Reservation | 装置・ユーザー・時間帯の組み合わせ |
| ユーザー | User | Keycloak の `sub` と紐づくアプリ DB 上の行（`id` / `keycloak_id` / `created_at` のみ。認証・プロフィールの正は Keycloak） |
| 管理者 | app-admin（レルムロール） | JWT の `realm_access.roles` に `KEYCLOAK_APP_ADMIN_REALM_ROLE`（既定 `app-admin`）が含まれると装置 CRUD 等の管理操作が許可される |
| ファセット検索 | facet search | カテゴリ・場所・状態などの次元で絞り込む検索 |
| 全文検索クエリ | `q`（クエリパラメータ） | 装置名等を対象とした検索文字列 |

## 2. ステータス（装置）

| 値 | 意味 |
|----|------|
| `available` | 利用可能 |
| `maintenance` | メンテナンス中 |
| `unavailable` | 利用不可 |
| `discontinued` | 製造終了・廃止（新規予約の運用方針は画面・API で表現。PoC では一覧表示用の状態値） |

## 3. ステータス（予約）

| 値 | 意味 |
|----|------|
| `confirmed` | 確定（時間枠として有効） |
| `cancelled` | キャンセル（重複判定から除外） |
| `completed` | 利用完了（将来の運用拡張用） |

**装置予約リストとキャンセル行**: リストでは **閲覧者本人の `cancelled` のみ**表示し、**他人の `cancelled` は表示しない**。カレンダーでは **`cancelled` を常に表示しない**（`GET .../reservations` の `calendar_mode=true`）。

**予約の論理削除**: `DELETE /api/reservations/{id}` は物理削除ではなく、**`confirmed` を `cancelled` に更新**する（冪等）。フロントの予約一覧キャンセルは **`PUT` で `status: cancelled`** でもよい。

## 4. UI / UX 用語

| 用語 | 定義 |
|------|------|
| デバウンス | 入力が止まってから一定時間後に検索を実行すること（300ms） |
| IME 入力中 | 日本語変換の未確定状態。確定までは検索を遅延させる |

## 5. インフラ・認証用語

| 用語 | 定義 |
|------|------|
| Realm | Keycloak におけるテナント境界（PoC では `master` を既定とする） |
| Client | Keycloak の OAuth クライアント（PoC では `device-reservation`） |
| JWT | `Authorization: Bearer` で送るアクセストークン |
