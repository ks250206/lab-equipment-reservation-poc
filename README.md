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
just deps-up         # PostgreSQL + Keycloak（既定: podman-compose）
# Docker の場合: export DEV_CONTAINER_RUNTIME=docker
just backend-dev     # 別ターミナル推奨
just frontend-dev    # http://localhost:5173
```

依存コンテナの停止: `just deps-down`。利用可能なレシピ一覧: `just` または `just --list`。

`just backend-check` の `pytest` は **PostgreSQL が起動していること**（`just deps-up` 済み、`.env` の `DATABASE_URL` が妥当）を前提とする。

### 手動での起動（just を使わない場合）

#### 1. 依存サービス起動

```bash
cd personal_space
podman-compose -f docker-compose.yml up -d
# または: just deps-up（同じく Podman 既定）
# Docker のみ使う場合: export DEV_CONTAINER_RUNTIME=docker && just deps-up
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

## ディレクトリ構成

```
personal_space/
├── AGENTS.md          # AI 向け必須ルール
├── doc/               # 恒久的ドキュメント（要求・設計・アーキテクチャ等）
├── README.md          # このファイル
├── Justfile           # just タスクランナー（起動・品質チェック）
├── scripts/           # compose 実行ラッパー等（just から呼ぶ）
├── flake.nix          # Nix 環境定義（just / uv / podman-compose 等）
├── docker-compose.yml # Keycloak + PostgreSQL
├── steering/          # イテレーション作業（README と iterations/）
├── backend/           # FastAPI
└── frontend/          # React
```