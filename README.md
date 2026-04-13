# 室内装置予約システム PoC

研究室内装置の予約・管理システム

## ドキュメント

| 種別 | パス |
|------|------|
| AI 向け必須ルール | [AGENTS.md](AGENTS.md) |
| 恒久的な設計・要求・開発手順 | [doc/](doc/)（例: `@doc/functional-design.md`） |

## 技術スタック

- **Backend**: Python 3.13, FastAPI, PostgreSQL, Keycloak (JWT)
- **Frontend**: React 19, Vite, Tailwind, shadcn/ui
- **Dev**: Nix (flake), pnpm, uv

## 起動方法

### クイックスタート（Nix + just）

`just` は [flake.nix](flake.nix) の devShell で提供されます。

```bash
cd personal_space
nix develop          # シェルに just / uv / Node 等が入る
just setup           # .env の雛形、uv sync、pnpm install（初回・環境変化時）
just deps-up         # Postgres + Keycloak（compose 重ね: 既定は開発プロファイル）
# Docker の場合: export DEV_CONTAINER_RUNTIME=docker
# Keycloak を Postgres 永続に: export PERSISTENCE_PROFILE=production（下記参照）
just backend-dev     # 別ターミナル推奨
just seed-dev        # 開発 DB に装置・ユーザー（ENVIRONMENT=development のみ）
just frontend-dev    # http://localhost:5173
```

依存コンテナの停止: `just deps-down`。利用可能なレシピ一覧: `just` または `just --list`。

`just backend-check` の `pytest` は **PostgreSQL が起動していること**（`just deps-up` 済み、`.env` の `DATABASE_URL` が妥当）を前提とする。

#### ポート 8000 が「既に使用中」でバックエンドが起動しないとき

別ターミナルの **取り残し `fastapi dev` / uvicorn** が `127.0.0.1:8000` を掴んでいることが多いです。

1. **何が掴んでいるか確認**（macOS / Linux）: `lsof -nP -iTCP:8000 -sTCP:LISTEN`
2. **終了**: 該当ターミナルで `Ctrl+C` を押すか、`just backend-free-port`（`8000` で LISTEN しているプロセスに `kill` を送る）
3. **別ポートで起動**（フロントの Vite プロキシは既定 `8000` 向きなので、変える場合は `frontend/vite.config.ts` の `target` も合わせる）:  
   `PORT=8001 just backend-dev` または `cd backend && PORT=8001 uv run fastapi dev`

### 手動での起動（just を使わない場合）

#### 1. 依存サービス起動

```bash
cd personal_space
just deps-up
# 手動の場合（開発プロファイル＝既定）:
#   bash scripts/compose.sh up -d
# Docker 利用時: export DEV_CONTAINER_RUNTIME=docker
```

#### 2. Nix 開発環境に入る

```bash
cd personal_space
nix develop
```

#### 3. バックエンド起動

```bash
cd backend
uv sync
uv run fastapi dev   # アプリ入口は backend/pyproject.toml の [tool.fastapi] entrypoint
```

#### 4. フロントエンド起動

```bash
cd frontend
cp .env.example .env   # 初回のみ。Keycloak URL 等を必要に応じて編集
pnpm install
pnpm dev
```

フロントは既定で `http://localhost:5173` を開き、`/api` は Vite のプロキシ経由で FastAPI（:8000）に転送されます。Keycloak でログインし、装置の閲覧・予約の作成ができます。

## サービスURL

| サービス | URL |
|---------|-----|
| FastAPI | http://localhost:8000 |
| OpenAPI (Swagger UI) | http://localhost:8000/docs |
| Vite | http://localhost:5173 |
| Keycloak | http://localhost:8080 |
| PostgreSQL | localhost:5432 |

## 初期設定 (Keycloak)

1. Keycloak 管理画面: http://localhost:8080 (admin/admin)
2. Realm: master (デフォルト)
3. Client 作成（ブラウザ SPA 用）:
   - Client ID: `device-reservation`
   - Client authentication: **Off**（パブリッククライアント）
   - Standard flow を有効化
   - Valid Redirect URIs: `http://localhost:5173/*`
   - Web Origins: `http://localhost:5173`

## 環境変数

| 場所 | 用途 |
|------|------|
| リポジトリルートの `.env.example` | バックエンド（`DATABASE_URL` 等） |
| `frontend/.env.example` | フロント（`VITE_KEYCLOAK_*` 等） |

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

## 永続化プロファイル（アプリ DB と Keycloak）

| レイヤー | 開発（既定） | 本番相当（`PERSISTENCE_PROFILE=production`） |
|----------|--------------|-----------------------------------------------|
| **アプリ DB**（装置・予約・`users` テーブル） | `DATABASE_URL` の Postgres（`docker-compose.yml` の `postgres`） | **同じく**接続先 URL を環境ごとに変える（クラウド RDS 等も可） |
| **Keycloak**（レルム・クライアント・ログインユーザ） | `KC_DB=dev-file`（コンテナ内。アプリ用 Postgres とは**別**） | `KC_DB=postgres` で **同一 Postgres サーバ上の `keycloak` DB** に保存（`docker/postgres/init/01-keycloak.sql` で DB 作成。初回ボリューム作成時のみ実行） |

- Keycloak は **アプリ DB とは独立**したストアですが、`production` プロファイルでは **Postgres に JDBC 接続**します（「DB 依存」と言えるのはこの意味）。
- 既存の Postgres ボリュームを流用しつつ **初めて production プロファイルにする**場合、`keycloak` ロール／DB が無いと Keycloak が起動に失敗します。そのときは DB に手動で `01-keycloak.sql` と同等の SQL を流すか、**開発用データ消去可なら** Postgres ボリュームを作り直してください。

### 開発シード（装置・ユーザー）

`ENVIRONMENT=development` のときのみ、`just seed-dev`（内部は `python -m app.seeding`）で以下を **冪等 upsert** します。

- **装置** 11 カテゴリ（XRD, XRF, XPS, 充放電装置, TG-DTA, グローブボックス, SEM, 3Dプリンタ, 蒸着装置, スパッタ装置, イオンミリング装置）× 3 台＝33 件（場所・ステータスにバリエーション）
- **ユーザー** 8 名（日本人名のダミー。1 名は管理者ロール。`keycloak_id` は `seed-...` 接頭辞）

本番（`ENVIRONMENT=production`）ではシードは拒否されます。

## ディレクトリ構成

```
personal_space/
├── AGENTS.md          # AI 向け必須ルール
├── doc/               # 恒久的ドキュメント（要求・設計・アーキテクチャ等）
├── README.md          # このファイル
├── Justfile           # just タスクランナー（起動・品質チェック）
├── scripts/           # compose.sh（Podman/Docker・永続プロファイル）
├── docker/            # Postgres init SQL 等
├── flake.nix          # Nix 環境定義（just / uv / podman-compose 等）
├── docker-compose.yml        # Postgres（共通）
├── docker-compose.dev.yml    # + Keycloak dev-file（開発既定）
├── docker-compose.prod.yml   # + Keycloak→Postgres keycloak DB（本番相当）
├── steering/          # イテレーション作業（README と iterations/）
├── backend/           # FastAPI
└── frontend/          # React
```