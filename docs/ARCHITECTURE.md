# Architecture

## Runtime Topology

```text
Browser
  -> frontend/ (HTML, CSS, JavaScript)
  -> /api/*
backend/app.py (FastAPI HTTP API)
  -> backend/database.py
  -> Alembic migrations
  -> data/cang_vu.db (SQLite local/pilot only)
  -> backend/xlsx_io.py (stdlib XLSX import/export)
```

The backend serves the frontend in local/single-host mode. Schema changes are
applied only through Alembic; runtime startup never creates or changes tables.
In production, a
reverse proxy may serve `frontend/` directly and proxy `/api/` to the Python
service. This keeps the front-door/backend contract separate from day one.

## Data Ownership

- `organizations`: reusable customer/company identity.
- `vessels`: current vessel master data.
- `declarations`: immutable-at-submit port-call snapshots plus cargo movement.
- `crew_members` and `declaration_crew`: reusable Crew List records and
  certificate snapshots attached to each voyage.
- `attachments`: metadata for images, PDF, Word, and Excel evidence stored on
  the persistent data volume.
- `integration_connectors` and `sync_jobs`: connector readiness plus prepared,
  auditable report payloads.
- `declaration_events`: append-only actor, role, status transition, note and
  correlation timeline for each arrival/departure permit.
- `audit_events`: append-only operational change history with actor,
  organization and correlation id.

## Persistence Contract

- One API write is one database unit of work; a failed request rolls back its
  session before release.
- Vessels, crew and declarations expose optimistic `version`; supplied stale
  versions receive `409 Conflict`.
- SQLite is limited to local/pilot single-node use. PostgreSQL cutover and
  production operations are governed by T4.

## Permit Workflow

Submitted declarations follow the ordered route `CV -> QLC -> BP -> ISSUE`.
The API rejects skipped stages and records each transition. Reviewers can
request changes with a reason; authorized BP operators can issue a permit
number or revoke an issued permit. Actor identity is derived from the
authenticated server-side user and cannot be supplied by the browser.

## Registry And Certificate Checks

The current registry check is deterministic and local: compare the stored
certificate expiry date with the server date, classify it as `VALID`,
`EXPIRING`, `EXPIRED`, or `UNKNOWN`, and record the check source in the audit
trail. It does not claim verification against an external registry.

An external registry adapter remains behind the connector boundary until an
authorized authority supplies an API contract, endpoint, credentials, rate
limits, and permitted data fields.

## Maritime Authority Sync Flow

```text
Submitted declarations
  -> select reporting period
  -> build versioned payload preview
  -> sync_jobs: PREPARED
  -> operator review
  -> authority connector (future, only after official contract)
  -> SENT / ACKNOWLEDGED / REJECTED receipt states (future)
```

The MVP never sends a prepared job automatically.

## Reporting Contract

- Appendix 1: declaration plan rows for a selected date.
- Appendix 2: monthly and year-to-month aggregate by cargo category, ship
  calls, and passengers.
- Appendix 3: one detailed row per submitted port call, split by movement type.

## Security Boundary

The MVP is a local/pilot runtime. Production deployment still requires company
authentication, HTTPS, backup/restore, retention rules, request-size limits,
rate limiting, attachment malware scanning, and an operator-approved
authorization matrix.
