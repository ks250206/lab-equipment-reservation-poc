# Implementation (Iteration 10 — Keycloak RBAC for app roles)

## Delivered

- **Authorization**: `require_admin` checks JWT `realm_access.roles` for `settings.keycloak_app_admin_realm_role` (default **`app-admin`**). No use of `users.role` for API authorization.
- **Dependencies**: `get_token_payload` decodes Bearer once per request; `get_current_user` builds on it. Tests override `get_token_payload` where admin flows are exercised without a real JWT.
- **`GET /api/users/me`**: Returns `UserResponse` with `role` derived from the token (`admin` vs `user`), not from the DB column.
- **`PUT /api/users/{id}`**: `UserUpdate` carries **`name` only**; role changes must be done in Keycloak.
- **User creation**: New DB rows always use `role=user` for the legacy column.
- **Keycloak seed** (`ensure_keycloak_app_admin_realm_role`): Idempotent realm role creation and mapping to `KEYCLOAK_SEED_GRANT_APP_ADMIN_USERNAME` (default `admin`), invoked from `just seed-dev` after SPA client seeding.
- **Removed**: `KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES` and preferred-username bootstrap in `auth.py`.
- **Frontend**: Admin users page edits display name only; copy explains Keycloak `app-admin` and that list `role` is DB-only.
- **Docs**: `doc/functional-design.md`, `doc/architecture.md`, `doc/keycloak-setup.md`, `.env.example` aligned with the above.

## Non-goals (unchanged)

- Full Keycloak Admin Console replacement, fine-grained ACLs beyond admin vs user, multi-realm beyond PoC defaults.
