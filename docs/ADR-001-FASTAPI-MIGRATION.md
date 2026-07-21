# ADR-001 — FastAPI Migration Strategy and Feature Parity Boundary

**Date**: 2026-07-11  
**Status**: ACCEPTED  
**Context**: Tranche T0 Baseline Recovery (WO-KBCV-T0-20260711)  
**Risk**: R2

## Decision

FastAPI with SQLAlchemy ORM is the confirmed target backend architecture for Quan-Ly-Xalan.
The previous Python stdlib (`http.server`) backend at commit `29ef124` is superseded.

## Rationale

- FastAPI provides OpenAPI spec generation, automatic validation via Pydantic, and async support needed for file uploads and future background jobs.
- SQLAlchemy enables schema migration via Alembic (T2), avoiding manual SQL construction.
- The migration is deliberately port-with-control (not full revert): behavior from `29ef124` is reviewed and ported to FastAPI; no blind copy-paste.

## Feature parity boundary (T0)

All 21 API calls from `frontend/app.js` are implemented as registered FastAPI routes.
Two features are intentionally limited in T0:

### `/api/vessels/{id}/verify-registry` — LOCAL ONLY
- Returns `registry_verification_source=local` only.
- Checks internal `certificate_expiry_date` for status computation.
- Does **not** call any external Maritime Authority registry API.
- **Reason**: No official API contract, endpoint URL, authentication spec or sandbox exists yet.
- **Deferred to**: T6 — once authority provides documented API spec, credentials and sandbox.

### `/api/integrations/prepare-sync` — PREPARED STATUS ONLY
- Creates a `SyncJob` with `status=PREPARED` containing the payload JSON.
- Does **not** send data to any external system.
- **Reason**: Same as above — no external API contract or credentials available.
- **Deferred to**: T6.

## Consequences

- UI entry points for both features remain visible; they show appropriate status badges.
- No silent 404 behavior: both endpoints return 200 with explicit `note` fields explaining deferral.
- T1 will address RBAC, tenant isolation and authorization gaps.
- T2 will introduce Alembic migrations and deprecate `create_all()` for production.
- T4 will address HTTPS, production deployment, structured logging.
- T5 will address UX improvement and framework migration decision (Vanilla JS vs React/Vue).

## Open architecture decisions remaining

- ADR-002: JWT bearer vs. secure cookie / BFF session (T1)
- ADR-003: SQLite-to-PostgreSQL cutover point (T2/T4)
- ADR-004: Attachment storage / quarantine provider (T3)
- ADR-005: Vanilla JS modularization vs. React/Vue migration (T5)
- ADR-006: Reporting template ownership and signed mapping version (T3)
