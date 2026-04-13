# Implementation (Iteration 2 — Database & Auth)

- **PostgreSQL** schema for core tables (`devices`, `users`, `reservations`) via SQLAlchemy 2.x async models.
- **Keycloak JWT** verification (`python-jose`, JWKS), FastAPI dependency for the current user with lazy DB sync.
- **User APIs**: `GET /api/users/me`, admin-only list/detail endpoints.
- Project layout split into `routers/`, `services/`, `schemas/`, and ORM `models/`.
