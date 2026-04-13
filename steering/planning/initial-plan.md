# 研究室装置予約システム PoC 実装計画

> 初期の全体メモ。詳細な恒久的仕様は `doc/`、進捗の表は `AGENTS.md` のイテレーション一覧を参照。

## 作成日

2026-04-13

## システム構成

```
┌─────────────────────────────┐
│     Client (Browser)        │
│  React + Vite + Tailwind  │
└────────────┬────────────────┘
             │ JWT (OIDC)
        ┌────┴────┐
        │Keycloak │
        │:8080    │
        └────┬────┘
             │ JWT
        ┌────┴────┐
        │FastAPI  │
        │:8000    │
        └────┬────┘
             │ async
        ┌────┴────┐
        │Postgres │
        │:5432    │
        └─────────┘
```

## 技術スタック

| レイヤー | 技術 | バージョン |
|---------|------|-----------|
| Python | uv, ty, ruff | 3.13 |
| Web | FastAPI + Pydantic | latest |
| DB | PostgreSQL + asyncpg | 16, latest |
| Frontend | React | 19 |
| Build | Vite | 6 |
| Package | pnpm | 9 |
| Node | node | v24.14.1 |
| Test | pytest (Python), vitest (React) | latest |
| Auth | Keycloak | 26 |

## リポジトリ（当時メモ）

```
lab-equipment-reservation-poc/
├── AGENTS.md
├── README.md
├── doc/
├── steering/
│   ├── README.md
│   ├── planning/
│   └── iterations/
├── backend/
└── frontend/
```

## データベース・API（概要）

恒久定義は `doc/functional-design.md` を参照。

## イテレーション計画（高レベル）

1. 基盤構築: Nix, Docker, FastAPI, React 初期化
2. DB + 認証: PostgreSQL, Keycloak JWT, ユーザー CRUD
3. 装置 CRUD: 装置モデル, API, テスト (80%+)
4. ファセット検索: インクリメンタル検索サービス
5. 予約機能: 予約 CRUD
6. フロントエンド: React UI + 認証フロー
7. リファクタリング: lint/fmt, カバレッジ確認

## ノート

- 型チェック: Python は `ty`、TS は `tsc --noEmit`
- カバレッジ目標: 80% 以上
- モックは使わない（TDD）
- 日本語デバウンス（IME 中はデバウンスしない）
