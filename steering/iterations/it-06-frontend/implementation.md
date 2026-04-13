# Implementation (Iteration 6 — Frontend)

- **Keycloak JS** (`keycloak-js`) with PKCE + `check-sso`, wrapped in **React Context** (`AuthProvider`, `useAuth`, token refresh via `updateToken`).
- **TanStack Query** for server state (devices, facets, reservations).
- **Routes**: home, device list (debounced search with **IME-aware** `useDebouncedValue`), device detail, reservations (login gate, create/delete).
- **API client** using `fetch` against `/api` (Vite dev proxy to FastAPI).
- **Tooling**: Vite `@` alias, `vite-env.d.ts`, Vitest + RTL for debounce hook, `.oxlintrc.json` ignore `dist/`.
