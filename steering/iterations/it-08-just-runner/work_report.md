# Work report — it-08-just-runner

## 2026-04-13

- `just` は flake に既に含まれていたため、ルート `Justfile` とドキュメントを中心に整備した。
- `DEV_CONTAINER_RUNTIME=podman` で README の `podman-compose` 経路と揃えた。Docker 既定は `docker compose` v2。
- 品質チェックは `just backend-check` / `just frontend-check` / `just check` でガイドラインのチェーンに対応。
