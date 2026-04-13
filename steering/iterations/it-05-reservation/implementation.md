# Implementation (Iteration 5 — Reservations)

- **Reservation** APIs under `/api/reservations`: list (current user), create, update, delete.
- **Business rules**: reject overlapping time ranges on the same device for non-`cancelled` reservations; validate interval ordering; `DELETE` returns **204 No Content**.
- **Create payload** excludes `user_id` (bound from JWT).
- **Service helpers**: `check_time_overlap`, persistence in `services/reservations.py`; router-level validation aligned with services.
- **Tests**: service tests + `tests/test_reservations_api.py` (ASGI client with dependency overrides).
