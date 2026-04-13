# 実装内容（イテレーション 8 — Just タスクランナー）

## スコープ

- ルート **Justfile** にグループ化したレシピ: 依存スタック（`deps-up` / `deps-down` / `deps-ps` / `deps-logs`）、初回 **setup**（環境ファイルスタブ、`uv sync`、`pnpm install`）、**dev** サーバ（`backend-dev`、`frontend-dev`）、`doc/development-guidelines.md` に沿った **check** チェーン。
- **Nix**: devShell に `just` は既存。Podman 手順を README どおりにするため **`podman-compose`** を追加。
- **ランタイム選択**: `scripts/compose.sh` と `DEV_CONTAINER_RUNTIME`（既定 **`podman`**。`docker` は `docker-compose` を優先し、なければ `docker compose`）により、Compose v2 プラグインが無い macOS でも Docker 利用時に動かしやすくした。

## 非目標

- Nix から Docker／Podman デーモンを管理しない（ホスト提供のまま）。
- 単一プロセスで「全部起動」するレシピは作らない（API + Vite は二ターミナル運用を推奨モデルとする）。
