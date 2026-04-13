# Work report — it-08-just-runner

## 2026-04-13

- `just` は flake に既に含まれていたため、ルート `Justfile` とドキュメントを中心に整備した。
- `DEV_CONTAINER_RUNTIME=podman` で README の `podman-compose` 経路と揃えた。Docker 既定は `docker compose` v2。
- 品質チェックは `just backend-check` / `just frontend-check` / `just check` でガイドラインのチェーンに対応。

## 2026-04-13（Podman 既定へ修正）

- 既定ランタイムを **Podman** に変更（`DEV_CONTAINER_RUNTIME` 未設定時）。Mac で `docker compose` が `-f` を誤解釈する環境を避ける。
- 依存コマンドを `scripts/compose.sh` に集約。Docker 側は **`docker-compose` を優先**し、無ければ `docker compose`（V2 プラグイン）を試す。
