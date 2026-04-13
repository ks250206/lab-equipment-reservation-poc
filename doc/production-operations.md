# 本番運用の操作指針（PoC 拡張想定）

本番クラウドへのデプロイ手順そのものはリポジトリ外（IaC・CI）に任せる前提で、**このアプリを本番相当で動かすときに揃えるべき設定と運用の要点**をまとめる。開発用の `start-dev` 付き Compose は **本番には流用しない**こと。

## 1. 前提となる構成イメージ

```
インターネット
  → TLS 終端（リバースプロキシ / LB）
  → 静的フロント（CDN またはオブジェクトストレージ + 同一オリジン配下の API プロキシ）
  → FastAPI（複数プロセス時はワーカー + リバースプロキシ）
  → PostgreSQL（アプリ DB + 必要なら Keycloak 用 DB を分離または同一クラスタの別 DB）
  → Keycloak（専用ホスト名、HTTPS）
```

PoC の `compose.prod.yml` は **単一ホスト上の検証**向け（Keycloak も `start-dev`）。本番では Keycloak 公式の **`start` + ビルド済みイメージ**、ホスト名・TLS・DB 接続プールを別途設計する。

## 2. 環境変数・シークレット

| 区分 | 変数（例） | 内容 |
|------|------------|------|
| アプリ | `ENVIRONMENT` | **`production`**（シード拒否・本番向け挙動） |
| DB | `DATABASE_URL` | 本番 Postgres の接続文字列（非同期ドライバ `asyncpg`）。接続先ファイアウォール・TLS はインフラ側で |
| JWT 検証 | `KEYCLOAK_URL` | **発行元と一致する** Keycloak の公開 URL（`https://auth.example.com` 等。**末尾スラッシュなし**推奨） |
| JWT 検証 | `KEYCLOAK_REALM` / `KEYCLOAK_CLIENT_ID` | 実レルム名・SPA のクライアント ID（バックエンドの audience / issuer 検証と一致） |
| フロント | `VITE_KEYCLOAK_URL` 等 | ブラウザから到達可能な Keycloak の URL（本番オリジン） |
| Keycloak シード用（開発のみ） | `KEYCLOAK_SEED_*` | **本番では使わない**（`just seed-dev` は `ENVIRONMENT=production` で拒否される） |

シークレットは **Git に入れない**（シークレットマネージャ、Kubernetes Secret、CI のマスク変数など）。

## 3. 依存サービス（本番相当の考え方）

- **PostgreSQL**: アプリ用 DB のバックアップ・リストア手順を別ドキュメントまたは運用 Runbook に用意する。
- **Keycloak**: レルム・クライアント・ユーザは **Keycloak 側のバックアップ**（DB ダンプまたは realm export）で保護。アプリの `users` テーブルとは別（[functional-design.md](functional-design.md) の Keycloak と DB の役割）。
- **永続化**: 本番では `KC_DB=postgres` 等の **外部 DB 接続**が一般的。PoC の `compose.prod.yml` は「同一 Postgres に `keycloak` DB」という簡略形。

## 4. アプリケーションの起動（概念）

### バックエンド

- 本番では **`fastapi run`** または **`uvicorn`** でワーカー数・`--proxy-headers` 等を指定（リバースプロキシの X-Forwarded-* を信頼する場合は明示的に）。
- このリポジトリの Just 例: `just backend-run-prod`（`ENVIRONMENT=production`）。実サーバでは systemd / container entrypoint に同様のコマンドを記述。
- **ホスト**: `APP_HOST` / `APP_PORT`（または `PORT`）をリスン先に合わせる。

### フロントエンド

- `pnpm run build` で `frontend/dist` を生成し、**静的ホスティング**または nginx 等で配信。
- **API ベース URL**: 本番では `VITE_API_BASE` を本番 API のオリジンまたは同一オリジン上のパスプレフィックスに設定（ビルド時に埋め込まれるため **再ビルドが必要**）。
- CORS: フロントオリジンと API オリジンが異なる場合は FastAPI 側で CORS を設定（PoC は Vite プロキシ依存が多い）。

## 5. デプロイ後の確認チェックリスト（最低限）

1. **ヘルス**: API のルートまたは既存のヘルスエンドポイントにアクセスし 200 になること。
2. **OIDC**: ブラウザからログイン〜ログアウトが一周すること（リダイレクト URI / Web origins が本番 URL になっていること）。
3. **JWT**: API 呼び出しで `401` が出ないこと（issuer / audience / 時刻ずれ）。
4. **DB マイグレーション**: 現 PoC は Alembic 等を含まない。スキーマ変更を本番で行う場合は手順を別途定義する。

## 6. ローカルでの「本番相当」検証

実本番の前に、同一リポジトリで次を推奨する（詳細は [local-development.md](local-development.md)）。

1. `just deps-down` のあと `just deps-up-prod`
2. `.env` を本番相当の URL・シークレットに寄せる（ローカルなら `localhost` のままでも可）
3. `just backend-run-prod` と `just frontend-build` → `just frontend-preview`

## 7. 関連ドキュメント

| 内容 | パス |
|------|------|
| 機能・API・データモデル | [functional-design.md](functional-design.md) |
| アーキテクチャ・スタック | [architecture.md](architecture.md) |
| Keycloak クライアント手動設定 | [keycloak-setup.md](keycloak-setup.md) |
| ローカル開発（Nix + just） | [local-development.md](local-development.md) |
