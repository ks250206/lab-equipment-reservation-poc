# 実装内容（イテレーション 28 — equipment-reservation 命名統一）

## スコープ

- **PostgreSQL**: アプリ DB 名を `equipment_reservation`、コンテナ名 `equipment-reservation-postgres`。
- **Keycloak**: 公開クライアント ID 既定を `equipment-reservation`（シード関数 `ensure_keycloak_equipment_reservation_client`）。
- **Python**: `pyproject.toml` の `name` を `equipment-reservation`（`uv.lock` 更新）。
- **MinIO 既定バケット**: `equipment-images`。画像サイズ上限は **`EQUIPMENT_IMAGE_MAX_BYTES`**（`DEVICE_IMAGE_MAX_BYTES` 互換）。
- **Compose**: MinIO / Keycloak の `container_name` を `equipment-reservation-*`。
- **フロント**: `VITE_KEYCLOAK_CLIENT_ID` 既定、`package.json` の `name`、TanStack Query のキャッシュキー接頭辞 `equipment-reservations`。
- **ドキュメント**: `doc/keycloak-setup.md` 等の Client ID・DB 名・MinIO 記述。

## 非目標

- REST パス `/api/devices` やドメインモデル `Device` のリネーム（API・スキーマ互換のため別イテレーション）。
