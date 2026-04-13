# 開発ガイドライン

コーディング、テスト、Git、イテレーション、フロント仕様の SSOT。

---

## 1. コーディング規約

- **Python**: `ruff` のルールに従う。フォーマットは `ruff format`。
- **型**: Pydantic で入出力を検証し、`ty` で静的に可能な限り検証する。
- **TypeScript**: プロジェクトの `oxlint` / `oxfmt` 設定に従う。
- **変更の粒度**: 依頼された課題に必要な最小差分とし、無関係なリファクタを混ぜない。

## 2. 命名規則

- Python: PEP 8 に沿った `snake_case`（モジュール・関数・変数）、`PascalCase`（クラス）。
- TypeScript/React: プロジェクト既存の慣習に合わせる。
- ドメイン用語は [@doc/glossary.md](glossary.md) を優先する。

## 3. テスト規約

- **モックは使わない**（DB・HTTP は実結合またはテスト用 DB／ASGI トランスポートで検証する）。
- **カバレッジ目標**: 80% 以上（Python: `pytest-cov`）。
- **Python**: `pytest`、非同期は `pytest-asyncio`（`asyncio_mode = auto`）。
- **React**: `vitest`。

## 4. Git 規約

- **イテレーション完了時**にローカルコミットする。
- **コミットメッセージ形式**: `{イテレーション番号}. {概要}`  
  例: `5. 予約APIの重複検証を追加`
- **イテレーション番号・コミット目安・進捗表**: [AGENTS.md](../AGENTS.md) の「イテレーション一覧」を唯一の SSOT とする（ここには複製しない）。
- **イテレーションと steering**: 着手順は下記「イテレーション開始時の steering」を必ず守る（[AGENTS.md](../AGENTS.md) 必須ルール 11 と同内容）。

## 5. リファクタリング基準

- 単一ファイルが **500 行超**、または責務が混在して読み取り困難なときに分割を検討する。
- 各イテレーションの完了時の **format / lint / test** および改善ループは [AGENTS.md](../AGENTS.md) の必須ルールおよび下記「イテレーション完了時の品質チェック」に従う。

## 5.1 イテレーション完了時の品質チェック（コマンド例）

**バックエンド**（`backend/` を変更した場合は必須）:

```bash
cd backend
uv run ruff format src tests
uv run ruff check src tests
uv run --extra test pytest tests/
```

型チェックをプロジェクトで採用している場合は `uv run ty check src/` も実行する（失敗時は修正ループに含める）。

**フロントエンド**（`frontend/` を変更した場合は必須）:

```bash
cd frontend
pnpm run format
pnpm run lint
pnpm run test
```

`pnpm run build`（`tsc --noEmit` を含む）で型エラーが拾える場合、イテレーション完了前に実行することを推奨する。

**フィードバックループ**: いずれかが失敗したらコードを直し、**同じチェーンを再度**実行する。リファクタ後も同様に再度 format → lint → test を通す。

## 5.2 `just`（タスクランナー）

ルートの [Justfile](../Justfile) で、依存コンテナの起動・停止、初回セットアップ、開発サーバ、品質チェックを短いコマンドにまとめている。`just` 実行ファイルは **Nix flake の devShell** に含める（`nix develop` 後に `just --list` で確認）。

| 用途 | コマンド例 |
|------|------------|
| レシピ一覧 | `just --list` |
| 依存サービス起動 / 停止 | `just deps-up` / `just deps-down`（**既定は Podman** / `podman-compose`） |
| Keycloak 永続化の切替 | `.env` の `PERSISTENCE_PROFILE=development`（既定: dev-file＋`keycloak_dev_data` ボリューム）または `production`（`just deps-up-prod`: Postgres の `keycloak` DB）。切替前は down 推奨（[doc/local-development.md](local-development.md)） |
| Docker のみ使う場合 | `export DEV_CONTAINER_RUNTIME=docker` のあと `just deps-up` 等 |
| 初回セットアップ | `just setup` |
| バックエンド開発 | `just backend-dev` |
| フロント開発 | `just frontend-dev` |
| 8000 番ポートの解放（開発サーバの取り残し） | `just backend-free-port`（macOS / Linux、`lsof` 利用） |
| 開発シード（装置・ユーザー） | `just seed-dev`（`ENVIRONMENT=development` のみ） |
| 本番相当 compose（Keycloak→Postgres） | `just deps-up-prod` / `just deps-down-prod` / `just deps-ps-prod` / `just deps-logs-prod`（[doc/local-development.md](local-development.md)） |
| 本番モード API / フロントプレビュー | `just backend-run-prod` / `just frontend-build` のあと `just frontend-preview` |
| バックエンド品質ループ | `just backend-check`（format → lint → test → ty）。`pytest` は DB 起動後（例: `just deps-up`）を前提 |
| フロント品質ループ | `just frontend-check` |
| 両方 | `just check` |

詳細は [doc/local-development.md](local-development.md) を参照する。

## 5.3 イテレーション開始時の steering（必須）

新しいイテレーション **N** に入るとき（依頼のスコープが「次のイテレーション」に相当するとき）、**リポジトリへ最初の変更を加える前**に次を行う。エージェント・人間のどちらでも同様。

1. **[AGENTS.md](../AGENTS.md)** の「イテレーション一覧」に行を追加する（コミット目安 `itN-...`、ステータスは **未着手** または **進行中** からでよい）。
2. **`steering/iterations/it-NN-<slug>/` ディレクトリを新規作成**する。`NN` は 2 桁ゼロ埋め、`<slug>` は短い **kebab-case の英語**（例: `persistence-seed`）。既存イテレーションと重複しない名前にする。
3. **次の 3 ファイルを必ず置く**（空の見出しだけでもよい。本文は **いずれも日本語** とし、役割の詳細は [steering/README.md](../steering/README.md) に従う）:
   - `implementation.md`（実装内容・スコープの要約）
   - `todo.md`（チェックリスト）
   - `work_report.md`（作業メモ）
4. コピー用の見出し例は [steering/planning/iteration-starter.md](../steering/planning/iteration-starter.md) を参照する。
5. **[steering/README.md](../steering/README.md)** の「インデックス（フォルダ名）」表に当該イテレーションの行を追加する。

**禁止**: steering の 3 ファイルが無い状態でイテレーション N の実装コミットだけを先行させること（後追い作成のみにしない）。

## 6. フロントエンド仕様（実装時）

- 日本語入力向け **デバウンス 300ms**。
- **IME 変換中はデバウンスしない**。
- サーバー状態は **React Query** で管理する。
- 認証状態は **React Context** で管理する。

## 7. イテレーション計画（高レベル）

1. 基盤構築: Nix, Docker, FastAPI, React 初期化  
2. DB + 認証: PostgreSQL, Keycloak JWT, ユーザー  
3. 装置 CRUD  
4. ファセット検索  
5. 予約 CRUD  
6. フロントエンド UI + 認証フロー  
7. リファクタリング・カバレッジ確認  
8. タスクランナー（`just`、Nix devShell）  
9. 永続化プロファイル切替・開発シード  

## 8. ドキュメント更新の責務

- **製品スコープ・要求・受け入れ**の変更 → `doc/product-requirements.md`
- **API・データモデル・振る舞い**の変更 → `doc/functional-design.md`
- **スタック・制約・NFR**の変更 → `doc/architecture.md`
- **ディレクトリ規約**の変更 → `doc/repository-structure.md`
- **開発ルール・Git・テスト・イテレーション着手（steering）**の変更 → 本ファイル（必要なら [steering/planning/iteration-starter.md](../steering/planning/iteration-starter.md) や [steering/README.md](../steering/README.md) も）
- **用語**の変更 → `doc/glossary.md`
- **エージェントの必須ルール**の変更、**イテレーション一覧の進捗**の更新 → `AGENTS.md` のみ（`doc/` に二重記載しない）
