# Architecture

## Runtime Topology

```text
Browser
  -> frontend/ (HTML, CSS, JavaScript)
  -> /api/*
backend/app.py (Python HTTP API)
  -> backend/database.py
  -> data/cang_vu.db (SQLite, persistent volume in production)
  -> backend/xlsx_io.py (stdlib XLSX import/export)
```

The backend serves the frontend in local/single-host mode. In production, a
reverse proxy may serve `frontend/` directly and proxy `/api/` to the Python
service. This keeps the front-door/backend contract separate from day one.

## Data Ownership

- `organizations`: reusable customer/company identity.
- `vessels`: current vessel master data.
- `declarations`: immutable-at-submit port-call snapshots plus cargo movement.
- `audit_events`: append-only operational change history.

## Reporting Contract

- Appendix 1: declaration plan rows for a selected date.
- Appendix 2: monthly and year-to-month aggregate by cargo category, ship
  calls, and passengers.
- Appendix 3: one detailed row per submitted port call, split by movement type.

## Security Boundary

The MVP is a local/pilot runtime. Production deployment still requires company
authentication, HTTPS, backup/restore, retention rules, request-size limits,
rate limiting, and an operator-approved authorization matrix.

