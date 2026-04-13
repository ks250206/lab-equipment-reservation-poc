# 実装内容（イテレーション 1 — 基盤）

## スコープ

- 再現可能な開発シェル用の Nix `flake.nix`。
- ローカルポートで **PostgreSQL** と **Keycloak** を起動する Compose（Podman 互換を含む）スタック。
- **FastAPI** バックエンドの骨格（`backend/`、`uv`、`pyproject.toml`）、アプリエントリポイントと設定のスタブ。
- **React + Vite** フロントの骨格（`frontend/`、`pnpm`）、TypeScript・Tailwind 系のベースライン。

設計の SSOT は `doc/` に置き、本イテレーションは実行可能なプロジェクト境界の確立にとどめた。
