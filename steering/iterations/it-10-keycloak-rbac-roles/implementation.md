# Implementation (Iteration 10 — Keycloak RBAC for app roles)

## Scope

- **Authorization source of truth** for “who is an app administrator” moves from PostgreSQL `users.role` to **Keycloak roles** carried in the access token (JWT).
- **Backend**: `require_admin` (and any other admin checks) derive privileges from token claims — typically **`realm_access.roles`** and/or **`resource_access[<client-id>].roles`**, using one agreed naming scheme (e.g. realm role `app-admin` or client role `admin` on `device-reservation`). Exact role names and hierarchy are fixed during implementation and documented in `doc/keycloak-setup.md` / `doc/functional-design.md`.
- **Keycloak automation**: extend development seeding (and documented manual steps) so the default admin user / test users receive the correct roles **idempotently** via Keycloak Admin API where feasible.
- **`GET /api/users/me`**: response still represents the app user row for FK/display, but the **`role` field exposed to the client** must reflect **Keycloak-derived** admin vs user (not stale DB-only semantics).
- **Admin UI / frontend**: show admin capabilities when the token implies admin (either by reusing `/users/me` after backend maps roles, or by reading token claims — pick one approach and document it).
- **Remove or deprecate** env-based bootstrap that only exists to promote DB `role` (`KEYCLOAK_BOOTSTRAP_ADMIN_USERNAMES` and dev-only auto-`admin` username logic in `auth.py`) once Keycloak roles are authoritative.

## Non-goals

- Replacing Keycloak Admin Console for full identity lifecycle (password reset, user deletion, etc.) — out of scope for this iteration.
- Fine-grained authorization beyond the existing **admin vs user** split (e.g. per-device ACLs) unless already implied by current APIs.
- Migrating **authentication** mechanics (still JWT + JWKS + same client); only **role-based authorization** moves to Keycloak claims.
- Multi-realm or multi-tenant Keycloak configuration beyond the current PoC defaults.

## Data model notes

- The `users.role` column may remain for **audit / legacy** with a clear rule (e.g. “ignored for auth, optional sync”) or be **removed** after a migration — decide in implementation and update `doc/functional-design.md` accordingly.
- **`PUT /api/users/{id}`**: if `role` is no longer stored in DB, either remove `role` from the update body or repurpose the endpoint to **no-op / 410 / delegate to Keycloak** with explicit product decision.

## Deliverables checklist (for closing the iteration)

- [ ] `doc/functional-design.md` and `doc/architecture.md` updated to describe Keycloak as the authority for app admin.
- [ ] `doc/keycloak-setup.md` updated with role names and how to assign them in the console.
- [ ] Backend tests use real JWT-shaped payloads (existing style) with/without role claims — **no mocks** for HTTP client to Keycloak in tests.
- [ ] `AGENTS.md` iteration row marked complete; `work_report.md` summarises outcomes.
