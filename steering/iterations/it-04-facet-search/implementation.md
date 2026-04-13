# Implementation (Iteration 4 — Facet Search)

- **`search_devices` service**: optional text query (`q`) plus filters for `category`, `location`, and `status` using SQLAlchemy `ilike` / equality conditions.
- **`get_facets`**: aggregates counts per dimension for the current result set (categories, locations, statuses).
- **HTTP surface**: `GET /api/devices` accepts facet query parameters; `GET /api/devices/facets` returns facet payloads.
- **Tests** in `tests/test_facet_search.py` for search + facets behaviour.
