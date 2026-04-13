# 機能設計書

システム構成、データモデル、API、主要な振る舞いの SSOT。

---

## 1. システム構成

```
Client (Browser) ─JWT─> Keycloak (:8080) ─JWT─> FastAPI (:8000) ─async─> PostgreSQL (:5432)
```

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

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | UUID | PK | ユーザーID |
| keycloak_id | VARCHAR(255) | UNIQUE, NOT NULL | Keycloak ユーザーID |
| email | VARCHAR(255) | NOT NULL | メールアドレス |
| name | VARCHAR(255) | NULL | 表示名 |
| role | ENUM | DEFAULT 'user' | ロール |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |

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

## 3. API 設計

### 3.1 装置 API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/devices | 任意 | 装置一覧（ファセット検索対応） |
| GET | /api/devices/{id} | 任意 | 装置詳細 |
| POST | /api/devices | 管理者 | 装置作成 |
| PUT | /api/devices/{id} | 管理者 | 装置更新 |
| DELETE | /api/devices/{id} | 管理者 | 装置削除 |
| GET | /api/devices/facets | 任意 | ファセット検索 |

### 3.2 ユーザー API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/users/me | 必須 | 現在のユーザー情報 |
| GET | /api/users | 管理者 | ユーザー一覧 |
| GET | /api/users/{id} | 管理者 | ユーザー詳細 |

### 3.3 予約 API

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| GET | /api/reservations | 必須 | ログインユーザーの予約一覧 |
| POST | /api/reservations | 必須 | 予約作成 |
| PUT | /api/reservations/{id} | 必須 | 予約更新 |
| DELETE | /api/reservations/{id} | 必須 | 予約削除（204 No Content） |

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

## 5. ユースケース・画面

PoC では画面遷移図・ワイヤフレームは省略。イテレーション6以降のフロント実装で補足する。

## 6. コンポーネント設計（バックエンド）

- **routers**: HTTP 入出力と依存性注入。
- **services**: ビジネスロジック・検索・永続化のオーケストレーション。
- **schemas**: Pydantic によるリクエスト／レスポンスモデル。
- **models**: SQLAlchemy ORM エンティティ。

詳細なファイル配置は [@doc/repository-structure.md](repository-structure.md)。
