# Implementation (Iteration 9 — Persistence profiles & dev seed)

## Scope

- **Compose split**: `compose.yml` (Postgres + init) + `compose.dev.yml` (Keycloak `KC_DB=dev-file`) + `compose.prod.yml` (Keycloak `KC_DB=postgres` targeting DB `keycloak` on the shared Postgres service). `scripts/compose.sh` selects the pair via `PERSISTENCE_PROFILE` (`development` default, `production` for the JDBC stack).
- **Postgres init**: `docker/postgres/init/01-keycloak.sql` creates role/database for Keycloak (runs on first volume init only).
- **App settings**: `ENVIRONMENT` / `APP_ENV` (`development` | `production`) with validation; `Settings()` reads `.env` from `backend/` or repo root (`env_file` tuple).
- **Dev seed**: `app.seeding` module — idempotent PostgreSQL upserts for 33 devices (11 lab categories × 3) and 8 Japanese dummy users (one admin). Guarded when `ENVIRONMENT=production`. `run_seed(session_factory=...)` for tests.
- **Just**: `seed-dev` recipe; `backend-test` uses `uv run --extra test` so pytest is available.

## Keycloak vs app DB

- **Development**: Keycloak realm data lives in **dev-file** storage (not the app’s `device_reservation` database).
- **Production profile**: Keycloak uses a **separate database** (`keycloak`) on the same Postgres server as the app — JDBC-backed persistence, independent schema from `device_reservation`.

## Non-goals

- No automatic seed on API startup.
- No Keycloak realm JSON import; SPA client setup remains manual (README).
