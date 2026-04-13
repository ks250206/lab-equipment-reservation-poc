# Work report — it-09-persistence-seed

## 2026-04-13

- Compose を分割し、`PERSISTENCE_PROFILE` で Keycloak の永続先（dev-file / Postgres）を切替可能にした。アプリ DB は従来どおり `DATABASE_URL` で切替。
- 開発シードは決定的 UUID と Postgres `ON CONFLICT` で再実行しても件数が増えないようにした。
- `Settings` がルート `.env` も読むようにし、`just backend-test` で pytest が見つからない問題を `--extra test` で解消。
