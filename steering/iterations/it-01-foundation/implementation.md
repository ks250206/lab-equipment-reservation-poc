# Implementation (Iteration 1 — Foundation)

- Nix `flake.nix` for a reproducible dev shell.
- Compose (or Podman-compatible) stack for **PostgreSQL** and **Keycloak** on local ports.
- **FastAPI** backend skeleton (`backend/`, `uv`, `pyproject.toml`) with app entrypoint and configuration stubs.
- **React + Vite** frontend skeleton (`frontend/`, `pnpm`) with baseline tooling (TypeScript, Tailwind pipeline).

Design SSOT lives under `doc/`; this iteration only established runnable project boundaries.
