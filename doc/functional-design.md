# 機能設計書

システム構成、データモデル、API、主要な振る舞いの SSOT。

---

## 1. システム構成

```
Client (Browser) ─JWT─> Keycloak (:8080) ─JWT─> FastAPI (:8000) ─async─> PostgreSQL (:5432)
                                                                    └─> MinIO (:9000, S3 互換・装置画像)
```

Keycloak のメタデータ永続化は **Compose のプロファイル**で切替える（`PERSISTENCE_PROFILE` / `just deps-up` と `just deps-up-prod`）。**開発（既定）**は dev-file（H2）を **名前付きボリューム**に載せてコンテナ再起動後も保持する。**本番相当**は同一 Postgres 上の **`keycloak` データベース**に JDBC 保存する。詳細は [doc/local-development.md](local-development.md) の「永続化プロファイル」。

## 2. データモデル定義

### 2.1 エンティティ概要

| エンティティ | 説明 |
|--------------|------|
| Device（装置） | 予約対象となる室内装置 |
| User（ユーザー） | Keycloak の `sub` と紐づく利用者 |
| Reservation（予約） | 装置とユーザーと時間帯の組 |

### 2.2 devices（装置）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | 装置ID |
| name | VARCHAR(255) | NOT NULL | 装置名 |
| description | TEXT | NULL | 説明 |
| location | VARCHAR(255) | NULL | 設置場所 |
| category | VARCHAR(100) | NULL | カテゴリ |
| status | ENUM | DEFAULT 'available' | ステータス（`available` / `maintenance` / `unavailable` / `discontinued`） |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | 更新日時 |
| image_object_key | VARCHAR | NULL | MinIO（S3）上のオブジェクトキー（画像ありのとき） |
| image_content_type | VARCHAR | NULL | 保存時の `Content-Type`（`image/png` または `image/jpeg`） |

### 2.3 users（ユーザー）

アプリ DB の `users` は **予約の `user_id` FK と Keycloak 主体（JWT の `sub`）の内部 UUID 対応**に加え、一覧表示用に **`email` / `name`（NULL 可）** を保持する（開発シードおよび初回ログイン時に JWT から同期。正のソースは Keycloak 側）。

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | アプリ内ユーザーID（`reservations.user_id` が参照） |
| keycloak_id | VARCHAR(255) | UNIQUE, NOT NULL | Keycloak のユーザー主体（JWT `sub` と一致） |
| email | VARCHAR(255) | NULL | 表示用メール（JWT またはシードから同期） |
| name | VARCHAR(255) | NULL | 表示用氏名（JWT またはシードから同期） |
| created_at | TIMESTAMP | NOT NULL | 当該主体が初めてアプリ DB に現れた日時 |

#### Keycloak とアプリ DB（users）の役割（現 PoC）

- **認証・本人確認・プロフィールの正**は Keycloak。アプリ DB にパスワードのマスタは持たない。
- **users 行の作成**: 初めてその `sub` で認証付き API にアクセスしたとき、`keycloak_id` と JWT 由来の `email` / `name` を設定して **INSERT** する（遅延作成）。既存行で `email` / `name` が NULL のときは JWT で **補完**する。
- **`GET /api/users/me`**: レスポンスの `id` / `keycloak_id` / `created_at` は DB 由来。`email` / `name` は JWT から合成（RFC 非準拠の場合はプレースホルダに正規化）。`role` は **`admin` または `user` のラベル**で、JWT の `realm_access.roles` に `KEYCLOAK_APP_ADMIN_REALM_ROLE`（既定 `app-admin`）が含まれるかのみで決める（DB 列は存在しない）。
- **`GET /api/users` / `GET /api/users/{id}`**（管理者）: DB の **`id` / `keycloak_id` / `created_at` のみ**を返す。メール・表示名の解決は Keycloak 管理コンソール等で行う（本 PoC では Admin API 連携はしない）。
- **ユーザー属性の変更**（メール・名前・パスワード・レルムロール）は Keycloak で行う。アプリ API に **`PUT /api/users/{id}` はない**。

### 2.4 reservations（予約）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | 予約ID |
| device_id | UUID | FK | 装置ID |
| user_id | UUID | FK | ユーザーID |
| start_time | TIMESTAMP | NOT NULL | 開始時刻 |
| end_time | TIMESTAMP | NOT NULL | 終了時刻 |
| purpose | TEXT | NULL | 使用目的 |
| status | ENUM | DEFAULT 'confirmed' | ステータス |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |

ER 図は PoC では省略するが、上記 FK 関係を正とする。

### 2.5 user_favorite_devices（装置お気に入り）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| user_id | UUID | PK（複合）, FK users | ユーザーID |
| device_id | UUID | PK（複合）, FK devices | 装置ID |
| created_at | TIMESTAMP | NOT NULL | 登録日時 |

- ユーザーと装置の **多対多のサブセット**（お気に入りフラグ）。`ON DELETE CASCADE` でユーザーまたは装置削除時に行も削除する。

### 2.1 開発シード（PoC）

- `ENVIRONMENT=development` のときのみ、`just seed-dev`（`python -m app.seeding`）で **装置・ユーザー** を冪等に投入できる（詳細は [doc/local-development.md](local-development.md)）。
- **利用者の正（SSOT）は Keycloak**。シードは先に Admin API でレルムユーザー（`seed-yamada` 等 8 名）を冪等に作成し、返却されたユーザー **id**（JWT の `sub` と一致）を `users.keycloak_id` に書き込む。氏名・メールは Keycloak 上の表現が正。パスワードは全員同一で環境変数 `KEYCLOAK_SEED_USER_PASSWORD`（既定 `SeedUsersDev1!`）を用いる。Keycloak に接続できない場合は **シード全体が失敗**する（装置のみ先に入れる挙動にはしない）。
- 続けて同一コマンドが Keycloak 管理 API に届く場合、**`KEYCLOAK_CLIENT_ID` の SPA クライアント**（公開クライアント・リダイレクト URI 等）を冪等に作成・更新し、レルムロール **`app-admin`** を冪等に作成して既定ユーザー（`KEYCLOAK_SEED_GRANT_APP_ADMIN_USERNAME`、既定 `admin`）へマッピングする（[doc/keycloak-setup.md](keycloak-setup.md) と整合）。Keycloak 未起動でクライアント／ロール設定に失敗した場合のみ従来どおりメッセージでスキップする（ユーザーシードより後段のため、ユーザー作成に成功していることが前提）。
- アプリ DB の `users.id` はシード用に **決定的 UUID**（名前空間付き uuid5）で固定し、予約シードの削除対象と FK を安定させる。JWT で初めて作られる一般ユーザー行とは **別行**として併存し得る。
- **予約シード**（`ENVIRONMENT=development` の `run_seed`）: 各装置に固定件数の `Reservation` を投入する。各予約の **`start_time` / `end_time` はシード実行時点の UTC における「当月 1 日 0:00」から「翌々月 1 日 0:00」までの半開区間内**に、装置ごとに重ならない 1 時間枠として **均等配置**する（ページング確認用）。**一部の行は `completed` または `cancelled`** とし、一覧・カレンダー表示の検証に使う。
- **装置画像シード**: MinIO への接続とバケット作成が可能なとき、各シード装置に **装置 ID から決定的に色・図形が変わる小さな PNG 1 枚**を投入し、`image_object_key` / `image_content_type` を更新する。MinIO 未起動などで失敗した場合はログに留め、DB・他シードは継続する。

## 3. API 設計

### 3.1 装置 API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/devices | 任意 | 装置一覧（ファセット検索対応・**ページング JSON**） |
| GET | /api/devices/{id} | 任意 | 装置詳細 |
| POST | /api/devices | 管理者 | 装置作成 |
| PUT | /api/devices/{id} | 管理者 | 装置更新 |
| DELETE | /api/devices/{id} | 管理者 | 装置削除 |
| GET | /api/devices/facets | 任意 | ファセット検索 |
| GET | /api/devices/{id}/image | 任意 | 装置画像のバイナリ（**PNG または JPEG**。画像が無いときは **404**） |
| POST | /api/devices/{id}/image | 管理者 | **multipart/form-data** で `file` 1 件をアップロードし、MinIO に保存して DB を更新する |

**装置レスポンスの `has_image` / `is_favorite`**

- `GET /api/devices` / `GET /api/devices/{id}` / 作成・更新の応答に **`has_image: boolean`** を含める（オブジェクトキー有無に相当）。フロントはプレースホルダ表示と `<img>` の出し分けに用いる。
- **`is_favorite: boolean`**（既定 `false`）: **Bearer 付き**でリクエストしたログインユーザーが当該装置をお気に入り登録しているか。未ログインまたはトークンなしでは常に `false`。

**`POST /api/devices/{id}/image` の検証（PoC）**

- **拡張子・MIME**: PNG / JPEG のみ（`Content-Type` は `image/png` または `image/jpeg`）。
- **容量**: 環境変数 `DEVICE_IMAGE_MAX_BYTES`（既定 **2 MiB**）以下。
- **内容**: 先頭バイトの粗判定に加え、**Pillow** で画像として解釈できること（改ざんされた拡張子を拒否）。

**`GET /api/devices` ページング**

- 応答は `{ "items": Device[], "total": number, "page": number, "page_size": number }`。
- `page`（任意、既定 **1**、最小 1）: 1 始まりのページ番号。
- `page_size`（任意、既定 **50**）: **20 / 50 / 100** のみ。他値は **422**。
- 並び順は **名称（`name`）昇順、同値時は `id` 昇順**（安定ソート）。
- `used_by_me`（任意、既定 `false`）: **true** のとき、ログインユーザーが **いずれかのステータスで一度でも予約したことのある装置**に限定する。未ログインで **true** を付けると **400**。
- `favorites_only`（任意、既定 `false`）: **true** のとき、ログインユーザーが **`user_favorite_devices` に登録した装置**に限定する。未ログインで **true** を付けると **400**。
- `used_by_me` と `favorites_only` を **同時に true** にすると両方の条件を **AND** する。

### 3.2 ユーザー API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/users/me | 必須 | 現在のユーザー情報（DB の紐付け＋ JWT 由来の `email` / `name` / `role` ラベル） |
| POST | /api/users/me/favorites/{device_id} | 必須 | 装置をお気に入りに追加（**204**。重複 POST も **204**） |
| DELETE | /api/users/me/favorites/{device_id} | 必須 | お気に入り解除（**204**。未登録でも **204**） |
| GET | /api/users | 管理者 | ユーザー一覧（`id` / `keycloak_id` / `created_at` のみ） |
| GET | /api/users/{id} | 管理者 | ユーザー詳細（同上） |

### 3.3 予約 API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/reservations | 必須 | ログインユーザーの予約一覧（**ページング JSON**・クエリで絞り込み） |
| GET | /api/devices/{device_id}/reservations | 必須 | 指定装置の予約一覧（ページング JSON。他ユーザーの枠も占有として返す PoC） |
| POST | /api/reservations | 必須 | 予約作成 |
| POST | /api/reservations/{id}/complete-usage | 必須 | **確定（confirmed）の予約のみ**を **`completed` に遷移**（本人のみ。それ以外は **409**）。完了報告の正規ルート |
| PUT | /api/reservations/{id} | 必須 | 予約更新（**既に `completed` の行は変更不可** → **409**。また **`status` を `completed` にする更新は常に 409**（完了は上記 POST のみ）） |
| DELETE | /api/reservations/{id} | 必須 | **論理キャンセル**（`confirmed` → `cancelled`、**204**）。既に `cancelled` なら冪等で **204**。**`completed` は不可** → **409** |

**`GET /api/reservations` クエリ**

- 応答は `{ "items": Reservation[], "total": number, "page": number, "page_size": number }`。各要素に **`user_name` / `user_email`**（予約者の DB プロフィール）を含む。
- `page`（任意、既定 **1**）、`page_size`（任意、既定 **50**、**20 / 50 / 100** のみ）。
- 並び順は **`start_time` 降順**（新しい枠が先）。
- `device_id`（任意）: 指定装置の予約に限定する。存在しない UUID は **404**。
- `reservation_status`（任意）: `confirmed` / `cancelled` / `completed` のいずれかで完全一致。不正値は **422**。
- `from` / `to`（任意、**セットで指定**）: 半開区間 `[from, to)` と時間が重なる予約のみ。片方だけは **400**。`from` ≥ `to` も **400**。
- `include_cancelled`（任意、既定 **`true`**）: **`false`** のときのみ、`reservation_status` 未指定の一覧から **キャンセル行を除く**（`reservation_status` 指定時はそのステータスで絞り、`include_cancelled` は無視してよい）。
- `favorites_only`（任意、既定 `false`）: **`true`** のとき、ログインユーザーが **お気に入り登録した装置**に紐づく予約行に限定する（`user_favorite_devices` に存在する `device_id` のみ）。

**`GET /api/devices/{device_id}/reservations` クエリ**

- 応答は `{ "items": Reservation[], "total": number, "page": number, "page_size": number }`。各 `Reservation` 要素には **`user_name` / `user_email`**（`users.name` / `users.email` のコピー。未設定時は `null`）が含まれる。
- `page`（任意、既定 **1**）、`page_size`（任意、既定 **50**、**20 / 50 / 100** のみ）。窓内の予約を **`start_time` 昇順**でページングする。
- `from` / `to`（任意、**セットで指定**）: 半開区間 `[from, to)` と時間が重なる予約のみ。片方だけの指定は **400**。`from` ≥ `to` も **400**。
- 省略時: サーバは **UTC 現在の前後 183 日**（約 6 ヶ月）の窓で返す。
- `include_cancelled`（任意、既定 `false`）: **API 互換のため残す**が、装置リストのキャンセル可視性は下記ルールが優先する。
- `calendar_mode`（任意、既定 `false`）: **`true`** のとき **キャンセル済みを閲覧者・他人問わず常に除外**（カレンダー用。フロントの窓取得で `true` を付与する）。
- `mine_only`（任意、既定 `false`）: **true** のときログインユーザー本人の予約行に限定する。
- `reservation_status`（任意）: `confirmed` / `cancelled` / `completed` のいずれかで完全一致。不正値は **422**。**`cancelled` 指定時は閲覧者本人のキャンセルのみ**（他人の `cancelled` は返さない）。
- **リスト（`calendar_mode` 未指定）**: 他人の `cancelled` は常に除外。閲覧者本人の `cancelled` は **`confirmed` / `completed` とともに返す**（時間窓内であれば）。
- 存在しない装置 ID は **404**。

**予約作成ボディ**

- `device_id`, `start_time`, `end_time`, `purpose`（任意）
- `user_id` は JWT から付与し、クライアントは送らない。

**重複ルール**

- 同一 `device_id` について、`status` が `cancelled` 以外の予約同士で時間帯が重なる作成・更新は **409 Conflict** とする（レスポンス本文の `detail` は **日本語の一文**で返す PoC 方針）。
- 更新時は対象予約自身を重複判定から除外する。
- `status` を `cancelled` に更新する場合は、上記重複チェックをスキップしてよい（キャンセル済み枠はブロックしない）。
- **`status` が既に `completed` の予約**は **PUT も DELETE も不可**（いずれも **409 Conflict**）。完了済みは監査・実績として固定する PoC 方針とする。

### 3.4 ファセット検索クエリパラメータ

装置一覧で利用可能なフィルタ:

- `q`: 全文検索クエリ
- `category`: カテゴリ
- `location`: 場所
- `status`: ステータス

## 4. 認証・認可

### 4.1 Keycloak（デフォルト設定）

- URL: `http://localhost:8080`
- Realm: `master`
- Client ID: `device-reservation`
- Web Origins / Redirect: `http://localhost:5173`（Vite 開発サーバー）

### 4.2 JWT フロー

1. フロントエンドが Keycloak で認証する。
2. アクセストークンは **keycloak-js** がメモリ上で保持する。初回および **ページリロード時**は `init({ onLoad: "check-sso", silentCheckSsoRedirectUri })` により、Keycloak のブラウザセッションが残っていれば非表示フローでトークンを再取得する（詳細は [@doc/keycloak-setup.md](keycloak-setup.md)）。
3. API 呼び出し時に `Authorization: Bearer <token>` を付与する。
4. バックエンドが JWKS で検証し、`sub` 等からユーザーを特定または作成する。

### 4.3 認可（管理者）

- **管理者**（装置の書き込み、`/api/users` の閲覧など）: アクセストークンの `realm_access.roles` に **`KEYCLOAK_APP_ADMIN_REALM_ROLE`（既定: `app-admin`）** が含まれること。
- 開発では `just seed-dev` が Keycloak Admin API で上記ロールの作成・ユーザーへのマッピングを試みる（手動手順は [doc/keycloak-setup.md](keycloak-setup.md)）。

## 5. ユースケース・画面

PoC では画面遷移図・ワイヤフレームは省略。イテレーション6以降のフロント実装で補足する。

- **マイページ（`/user`）**: ログイン中は `GET /api/users/me` に基づき、表示名・メール・ロール（JWT 由来ラベル）・Keycloak 主体 ID・アプリ DB 登録日時を表示する。未ログイン時はログインへ誘導する。
- **ヘッダー右**: 未認証は **ログイン**（Keycloak へ誘導）。認証済みは **マイページ**（`/user`）リンクと **ログアウト**。
- **装置一覧（`/devices`）**: ページング UI（`ListPaginationBar`）は **検索結果リストの上**に置く。ログイン時は **使ったことがある装置のみ**（`used_by_me=1`）、**お気に入りのみ**（`favorites_only=1`）をチェックで切り替え可能（API は `Authorization` 必須）。一覧取得時に **`is_favorite`** が返ればお気に入り行に星アイコンを表示する。装置詳細から `?category=` / `?location=` で戻ったときは URL に合わせてフィルタを同期する。**表示モード**として **サムネ（既定）・リスト・詳細**を切り替え可能。サムネ／詳細では `GET /api/devices/{id}/image` を参照するサムネ枠を表示し、**画像なしまたは読み込み失敗時はプレースホルダ**（「画像なし」等）を出す。**サムネ／詳細の画像枠は `/devices/{id}` へのリンク**（`DeviceImageSlot` の `to`）とし、タイトルと同様に詳細へ遷移できる。**フィルタ・ページ・`view`（表示モード）**はクエリ文字列と双方向同期し、ブックマーク・共有・ブラウザの戻る／進むに利用できる。
- **予約一覧（`/reservations`）**: **あなたの予約**は `GET /api/reservations` のページング・クエリ（装置・ステータス・期間・**キャンセル行の既定表示**・**お気に入りのみ `favorites_only`**）と **URL クエリ**を同期する。ステータスが「指定なし」のときは **API 既定でキャンセル行も含める**（一覧から隠すチェックで `include_cancelled=false` を付ける）。**キャンセル成功・利用完了報告成功**のあと、画面右下に **スナックバー（Radix Toast）**で進捗を通知する。新規予約のフォームは置かず、**装置一覧／装置詳細のカレンダー**から `POST /api/reservations` で作成する。各行から **編集**（ダイアログで `PUT`）と、確定中のみ **キャンセル**（`PUT` で `cancelled`、Lucide の **Ban** アイコンのみ。文言「削除」は使わない）。**`completed` / `cancelled` 行にはキャンセル操作を出さない**。編集ダイアログは完了行は閲覧のみ（API も **409**）。**利用完了（`completed`）への遷移**は **`/reservations/usage-complete`** の専用画面から `POST /api/reservations/{id}/complete-usage` のみ（`PUT` での完了は **409**）。装置・予約の **ステータスはタグ風バッジ**で色分け表示する。
- **装置詳細の予約リスト**: **すべて / 自分のみ**の切り替えと **ステータス**のセレクトで API（`mine_only` / `reservation_status`）に同期する。表の右端に **編集**ボタン（Lucide の鉛筆アイコン）。自分の予約は編集可能、他者は閲覧のみで同じ詳細ダイアログを開く。**カレンダー**ではイベントの**表示テキストは利用者名のみ**とし、**時刻レンジ＋名前**は要素の HTML `title`（ツールチップ）に載せる。**自分の予約はティール系・他ユーザーはスレート系**の背景色で区別する。
- **装置詳細**: タイトル横に **お気に入り**トグル（`POST` / `DELETE /api/users/me/favorites/{device_id}`）。**パンくず**（装置一覧 > 設置場所 > 装置名）。設置場所の段は **`/devices?location=...`** へのリンク。カテゴリ・設置場所の値は **`/devices?category=...` / `?location=...`** へのリンク（React Router の `Link`、DOM 上はアンカー）。**レイアウト右側**に装置画像（同上のサムネ枠）。**管理者**はファイル選択で `POST /api/devices/{id}/image` により画像を登録・差し替えできる。
- **装置詳細の予約（リスト / カレンダー）**: リスト表示でもページングは **表の上**。**月表示**では 1 日あたり表示件数に上限を設け、超過分は **「+N件」** 形式のリンクで省略する。イベントをクリックすると **詳細モーダル**を開く（編集可否は上記リストの項と同様）。**カレンダー（月・週・日）**では、空き枠を **ドラッグ選択**するとその範囲（FullCalendar の `end` は排他）を開始・終了として `POST /api/reservations` で新規予約できる。既存予約と重なる範囲は選択できない（`selectOverlap: false`）。
- **利用完了報告（`/reservations/usage-complete`）**: ログイン後、`GET /api/reservations` を **`reservation_status=confirmed`** でページング表示し、各行から **`POST /api/reservations/{id}/complete-usage`** で完了報告する。ヘッダーに **利用完了報告** へのナビリンクを置く。

## 6. コンポーネント設計（バックエンド）

- **routers**: HTTP 入出力と依存性注入。
- **services**: ビジネスロジック・検索・永続化のオーケストレーション。
- **schemas**: Pydantic によるリクエスト／レスポンスモデル。
- **models**: SQLAlchemy ORM エンティティ。

詳細なファイル配置は [@doc/repository-structure.md](repository-structure.md)。
