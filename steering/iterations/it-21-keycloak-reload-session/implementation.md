# 実装内容（イテレーション 21 — リロード後も Keycloak セッションを復元）

## スコープ

- `keycloak-js` の `init()` に `onLoad: "check-sso"` と `silentCheckSsoRedirectUri` を指定し、**フルリロード後も** Keycloak 側に残っているブラウザセッションからトークンを再取得する。
- `checkLoginIframe: false` とし、サードパーティ Cookie に依存するログイン状態 iframeは使わない。
- `frontend/public/silent-check-sso.html` を追加（Keycloak 公式と同様に `postMessage` で親へコールバック URL を渡す）。

## 非目標

- Keycloak サーバ側のレルム／セッション設定の変更（既存の Valid redirect URIs のワイルドカードで十分な想定）。

## 補足

- 手動でクライアントを作っている環境では、**Valid redirect URIs** に `silent-check-sso.html` が含まれること（例: `http://localhost:5173/*`）を確認する。
