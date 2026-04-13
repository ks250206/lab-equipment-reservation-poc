# Implementation (Iteration 3 — Device CRUD)

- **Device** ORM entity and Pydantic request/response models.
- **Device service** layer (`create`, `get`, `list`, `update`, `delete`) and **FastAPI router** under `/api/devices` with admin protection for mutating routes.
- **pytest** coverage for device flows (no mocks; real async DB session per tests).
