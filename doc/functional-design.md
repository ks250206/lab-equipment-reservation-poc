# 機能設計書

システム構成、データモデル、API、主要な振る舞いの SSOT。

---

## 1. システム構成

```
Client (Browser) ─JWT─> Keycloak (:8080) ─JWT─> FastAPI (:8000) ─async─> PostgreSQL (:5432)
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
| status | ENUM | DEFAULT 'available' | ステータス |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | 更新日時 |

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

### 2.1 開発シード（PoC）

- `ENVIRONMENT=development` のときのみ、`just seed-dev`（`python -m app.seeding`）で **装置・ユーザー** を冪等に投入できる（詳細は [doc/local-development.md](local-development.md)）。
- **利用者の正（SSOT）は Keycloak**。シードは先に Admin API でレルムユーザー（`seed-yamada` 等 8 名）を冪等に作成し、返却されたユーザー **id**（JWT の `sub` と一致）を `users.keycloak_id` に書き込む。氏名・メールは Keycloak 上の表現が正。パスワードは全員同一で環境変数 `KEYCLOAK_SEED_USER_PASSWORD`（既定 `SeedUsersDev1!`）を用いる。Keycloak に接続できない場合は **シード全体が失敗**する（装置のみ先に入れる挙動にはしない）。
- 続けて同一コマンドが Keycloak 管理 API に届く場合、**`KEYCLOAK_CLIENT_ID` の SPA クライアント**（公開クライアント・リダイレクト URI 等）を冪等に作成・更新し、レルムロール **`app-admin`** を冪等に作成して既定ユーザー（`KEYCLOAK_SEED_GRANT_APP_ADMIN_USERNAME`、既定 `admin`）へマッピングする（[doc/keycloak-setup.md](keycloak-setup.md) と整合）。Keycloak 未起動でクライアント／ロール設定に失敗した場合のみ従来どおりメッセージでスキップする（ユーザーシードより後段のため、ユーザー作成に成功していることが前提）。
- アプリ DB の `users.id` はシード用に **決定的 UUID**（名前空間付き uuid5）で固定し、予約シードの削除対象と FK を安定させる。JWT で初めて作られる一般ユーザー行とは **別行**として併存し得る。
- **予約シード**（`ENVIRONMENT=development` の `run_seed`）: 各装置に固定件数の `Reservation` を投入する。各予約の **`start_time` / `end_time` はシード実行時点の UTC における「当月 1 日 0:00」から「翌々月 1 日 0:00」までの半開区間内**に、装置ごとに重ならない 1 時間枠として **均等配置**する（ページング確認用）。

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

**`GET /api/devices` ページング**

- 応答は `{ "items": Device[], "total": number, "page": number, "page_size": number }`。
- `page`（任意、既定 **1**、最小 1）: 1 始まりのページ番号。
- `page_size`（任意、既定 **50**）: **20 / 50 / 100** のみ。他値は **422**。
- 並び順は **名称（`name`）昇順、同値時は `id` 昇順**（安定ソート）。

### 3.2 ユーザー API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/users/me | 必須 | 現在のユーザー情報（DB の紐付け＋ JWT 由来の `email` / `name` / `role` ラベル） |
| GET | /api/users | 管理者 | ユーザー一覧（`id` / `keycloak_id` / `created_at` のみ） |
| GET | /api/users/{id} | 管理者 | ユーザー詳細（同上） |

### 3.3 予約 API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/reservations | 必須 | ログインユーザーの予約一覧 |
| GET | /api/devices/{device_id}/reservations | 必須 | 指定装置の予約一覧（ページング JSON。他ユーザーの枠も占有として返す PoC） |
| POST | /api/reservations | 必須 | 予約作成 |
| PUT | /api/reservations/{id} | 必須 | 予約更新 |
| DELETE | /api/reservations/{id} | 必須 | 予約削除（204 No Content） |

**`GET /api/devices/{device_id}/reservations` クエリ**

- 応答は `{ "items": Reservation[], "total": number, "page": number, "page_size": number }`。各 `Reservation` 要素には **`user_name` / `user_email`**（`users.name` / `users.email` のコピー。未設定時は `null`）が含まれる。
- `page`（任意、既定 **1**）、`page_size`（任意、既定 **50**、**20 / 50 / 100** のみ）。窓内の予約を **`start_time` 昇順**でページングする。
- `from` / `to`（任意、**セットで指定**）: 半開区間 `[from, to)` と時間が重なる予約のみ。片方だけの指定は **400**。`from` ≥ `to` も **400**。
- 省略時: サーバは **UTC 現在の前後 183 日**（約 6 ヶ月）の窓で返す。
- `include_cancelled`（任意、既定 `false`）: `true` のとき `cancelled` 行も含める。
- 存在しない装置 ID は **404**。

**予約作成ボディ**

- `device_id`, `start_time`, `end_time`, `purpose`（任意）
- `user_id` は JWT から付与し、クライアントは送らない。

**重複ルール**

- 同一 `device_id` について、`status` が `cancelled` 以外の予約同士で時間帯が重なる作成・更新は **409 Conflict** とする。
- 更新時は対象予約自身を重複判定から除外する。
- `status` を `cancelled` に更新する場合は、上記重複チェックをスキップしてよい（キャンセル済み枠はブロックしない）。

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
2. アクセストークンを保存する（実装方針は [@doc/architecture.md](architecture.md) / フロント実装に従う）。
3. API 呼び出し時に `Authorization: Bearer <token>` を付与する。
4. バックエンドが JWKS で検証し、`sub` 等からユーザーを特定または作成する。

### 4.3 認可（管理者）

- **管理者**（装置の書き込み、`/api/users` の閲覧など）: アクセストークンの `realm_access.roles` に **`KEYCLOAK_APP_ADMIN_REALM_ROLE`（既定: `app-admin`）** が含まれること。
- 開発では `just seed-dev` が Keycloak Admin API で上記ロールの作成・ユーザーへのマッピングを試みる（手動手順は [doc/keycloak-setup.md](keycloak-setup.md)）。

## 5. ユースケース・画面

PoC では画面遷移図・ワイヤフレームは省略。イテレーション6以降のフロント実装で補足する。

- **マイページ（`/user`）**: ログイン中は `GET /api/users/me` に基づき、表示名・メール・ロール（JWT 由来ラベル）・Keycloak 主体 ID・アプリ DB 登録日時を表示する。未ログイン時はログインへ誘導する。
- **ヘッダー右**: 未認証は **ログイン**（Keycloak へ誘導）。認証済みは **マイページ**（`/user`）リンクと **ログアウト**。

## 6. コンポーネント設計（バックエンド）

- **routers**: HTTP 入出力と依存性注入。
- **services**: ビジネスロジック・検索・永続化のオーケストレーション。
- **schemas**: Pydantic によるリクエスト／レスポンスモデル。
- **models**: SQLAlchemy ORM エンティティ。

詳細なファイル配置は [@doc/repository-structure.md](repository-structure.md)。
