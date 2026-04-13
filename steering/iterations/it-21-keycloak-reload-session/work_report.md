# 作業レポート — it-21-keycloak-reload-session

- 2026-04-13 着手。keycloak-js の `onLoad` 未指定ではリロード時にトークン復元が走らないことを確認し、`check-sso` + silent リダイレクトで対応した。
