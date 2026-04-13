# 実装内容（イテレーション 6 — フロントエンド）

## スコープ

- **Keycloak JS**（`keycloak-js`）を PKCE と `check-sso` で利用し、**React Context**（`AuthProvider`、`useAuth`、`updateToken` によるトークン更新）でラップ。
- **TanStack Query** によるサーバー状態（装置、ファセット、予約）。
- **ルート**: ホーム、装置一覧（**IME 対応**の `useDebouncedValue` によるデバウンス検索）、装置詳細、予約（ログインゲート、作成／削除）。
- **`/api` 向け `fetch` の API クライアント**（Vite 開発プロキシで FastAPI に転送）。
- **ツール**: Vite の `@` エイリアス、`vite-env.d.ts`、デバウンス用フックの Vitest + RTL、`.oxlintrc.json` で `dist/` を無視。
