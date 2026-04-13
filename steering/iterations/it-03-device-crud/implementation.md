# 実装内容（イテレーション 3 — 装置 CRUD）

## スコープ

- **装置** の ORM エンティティと Pydantic のリクエスト／レスポンスモデル。
- **装置サービス**（`create`、`get`、`list`、`update`、`delete`）と **`/api/devices`** 配下の FastAPI ルータ。変更系ルートは管理者保護。
- 装置フロー向け **pytest**（モックなし。テストごとに実 async DB セッション）。
