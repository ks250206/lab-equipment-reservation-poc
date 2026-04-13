# Implementation (Iteration 8 — Just task runner)

## Scope

- Root **Justfile** with grouped recipes: dependency stack (`deps-up` / `deps-down` / `deps-ps` / `deps-logs`), first-time **setup** (env file stubs, `uv sync`, `pnpm install`), **dev** servers (`backend-dev`, `frontend-dev`), and **check** chains aligned with `doc/development-guidelines.md`.
- **Nix**: `just` was already in the devShell; added **`podman-compose`** so Podman workflows match README without extra installs.
- **Runtime selection**: `DEV_CONTAINER_RUNTIME` (`docker` default, `podman` for `podman-compose`) keeps one Justfile for both ecosystems.

## Non-goals

- No Docker/Podman daemon management from Nix (still host-provided).
- No single-process “run everything” recipe (two terminals for API + Vite remain the supported model).
