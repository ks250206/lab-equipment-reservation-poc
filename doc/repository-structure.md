# リポジトリ構造定義書

フォルダ・ファイル構成と役割の SSOT。

---

## 1. リポジトリルート

```
personal_space/
├── AGENTS.md              # エージェント必須ルール（短い）
├── README.md              # 人間向け: 概要・起動手順
├── doc/                   # 恒久的設計ドキュメント（@doc/ で参照）
├── flake.nix
├── Justfile               # just: 依存起動・dev サーバ・品質チェック
├── scripts/               # compose.sh（永続プロファイル含む）
├── docker/                # Postgres init（keycloak DB 等）
├── .env                   # gitignore（ローカル秘密）
├── .env.example
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── steering/              # イテレーション作業（iterations/ 参照。設計SSOTではない）
├── backend/               # FastAPI
└── frontend/              # React + Vite
```

## 2. ドキュメントの役割

| パス | 役割 |
|------|------|
| `AGENTS.md` | AI が**必ず守る**ルールのみ |
| `doc/*.md` | 要求・機能設計・アーキテクチャ等の**恒久的**な詳細 |
| `README.md` | クローン直後の人間向けクイックスタート |
| `steering/` | イテレーション単位の TODO・実装メモ・作業報告（[steering/README.md](../steering/README.md)） |

### 2.1 `steering/` の中身

```
steering/
├── README.md                 # 運用ルール・インデックス
├── planning/
│   ├── initial-plan.md       # PoC 初期の全体メモ
│   └── iteration-starter.md  # 新イテレーション用 3 ファイルのコピー用テンプレ
└── iterations/
    └── it-NN-<slug>/         # 例: it-06-frontend
        ├── implementation.md # 実装内容（英語で記載する）
        ├── todo.md           # チェックリスト
        └── work_report.md    # 作業報告・判断ログ
```

## 3. バックエンド（`backend/`）

```
backend/
├── pyproject.toml
├── src/app/
│   ├── main.py           # FastAPI アプリ生成・ルータ登録
│   ├── config.py         # 設定・列挙型
│   ├── auth.py           # JWT 検証・現在ユーザー
│   ├── db.py             # エンジン・セッション
│   ├── schemas/          # Pydantic（API I/O）
│   ├── models/           # SQLAlchemy ORM
│   ├── routers/          # エンドポイント
│   └── services/         # ビジネスロジック
└── tests/                # pytest（モックなし）
```

## 4. フロントエンド（`frontend/`）

```
frontend/
├── package.json
├── vite.config.ts          # `@` → src エイリアス、/api プロキシ
├── vitest.config.ts
├── .env.example            # VITE_KEYCLOAK_* 等
├── src/
│   ├── auth/               # Keycloak + React Context
│   ├── api/                # fetch クライアント・型
│   ├── components/
│   ├── hooks/              # 例: IME 対応デバウンス
│   ├── pages/
│   ├── env.ts
│   └── main.tsx
└── tests/                  # Vitest
```

## 5. ファイル配置ルール

- **新規 API**: `routers/` にルート、`services/` に処理、`schemas/` に入出力モデル。
- **DB スキーマ変更**: ORM（`models/`）とマイグレーション方針（採用している場合）を同期する。PoC で自動生成のみの場合は `doc/functional-design.md` を更新する。
- **環境変数**: 追加時は `.env.example` と `config` 読み取りを更新する。
