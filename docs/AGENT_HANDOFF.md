# CVF Agent Handoff

## Tranche: T0 Baseline Recovery (WO-KBCV-T0-20260711)

- **Status**: CLOSED — Gate 0 PASSED and committed
- **Date**: 2026-07-11
- **Phase**: BUILD
- **Risk Level**: R2

### What was done (T0)

| Task | Status |
|------|--------|
| T1 — API Contract inventory | ✅ DONE — `docs/API_CONTRACT.md` |
| T2 — Runtime baseline | ✅ DONE — `backend/__init__.py`, pinned requirements, fixed `run-dev.ps1` |
| T3 — Restore API feature parity | ✅ DONE — all 21 frontend endpoints implemented |
| T4 — Validation and transaction safety | ✅ DONE — Pydantic models, ETA/ETD check, submitted-record protection |
| T5 — Rebuild automated tests | ✅ DONE — 32 tests PASS (pytest + httpx TestClient) |
| T6 — Documentation | ✅ DONE — README, ADR-001, API_CONTRACT, HANDOFF updated |

### Test results (Gate 0 verification)

```
32 passed, 0 failed — 4.64s
Python 3.13.12 | pytest 8.2.0
```

Closure commit: `6c8917d` (`feat: restore FastAPI baseline and API contract`)

Final reviewer evidence:

- Tests: 32 passed, 0 failed.
- `git diff --check`: PASS.
- CVF Workspace Doctor: PASS 17/17.
- Runtime database and attachments: not committed.

Test categories covered:
- health + static frontend
- auth (login, wrong password, protected route)
- vessel CRUD + registry verify
- crew CRUD
- declaration draft + submit
- TEU calculations
- workflow CV→QLC→BP→ISSUE (ordered, skip rejected)
- submitted record edit protection (409)
- attachment signature + size validation
- XLSX report appendix 1/2/3
- route coverage (all 21 frontend paths registered)
- suggestions
- integrations (status + prepare-sync)
- crew snapshot on declaration

### Deferred items (intentional T0 scope boundary)

| Feature | Status | Next Tranche |
|---------|--------|-------------|
| `/api/vessels/{id}/verify-registry` — external API | Local-only | T6 |
| `/api/integrations/prepare-sync` — actual send | PREPARED only, no external call | T6 |
| RBAC / tenant isolation | Auth works, authorization gaps noted | T1 |
| Alembic migrations | `create_all()` still used locally | T2 |
| HTTPS / security headers | Not configured | T4 |
| Production data migration | No action | T2/T4 |
| `schemas.py` Pydantic V2 migration | Warns but works | T2 tech debt |

### Security gaps recorded for T1

- `allow_origins=["*"]` CORS — needs allowlist per environment
- JWT secret is env-injectable but falls back to hardcoded default (fail-fast needs to be added for non-local)
- No RBAC: authenticated user can access all data regardless of role/organization
- localStorage token storage — secure alternative (ADR-002) deferred to T1
- No rate limiting on `/api/auth/login`

### Pre-existing issues NOT in T0 scope

- `frontend/app.js:448` trailing whitespace — pre-existing, not introduced by T0
- `backend/schemas.py` Pydantic V2 `orm_mode` deprecation warnings — T2 tech debt
- `backend/auth.py` `datetime.utcnow()` deprecation — T2 tech debt

### Next governed move

**T1 — Identity, RBAC and tenant isolation** (R2, human BUILD approval required):
1. Define role matrix: CUSTOMER, CV, QLC, BP, ADMIN
2. Bind user to organization; scope all customer queries
3. Remove JWT default secret; add fail-fast for non-local environments
4. Endpoint-level authorization + negative tests per role
5. CORS allowlist per environment
6. Rate limit login, password policy, audit login events

Work order issued: `docs/WORK_ORDER_T1_IDENTITY_RBAC_TENANT_ISOLATION.md`
(`WO-KBCV-T1-20260711`, READY FOR ASSIGNMENT).

### Human review closure record

1. ✅ Tests: `32 passed, 0 failed`
2. ✅ Gate 0: health, frontend, critical workflow PASS (verified by test suite)
3. ✅ No unexpected 404 on frontend endpoints
4. ✅ Test database isolated from `data/cang_vu.db`
5. ✅ No hard-coded production secret added
6. ✅ `data/` directory untouched
7. ✅ `git diff --check`: PASS after reviewer cleanup
8. ✅ Human owner authorized commit
9. ✅ CVF doctor re-run at handoff: PASS 17/17

---

## Tranche: T1 Identity, RBAC and Tenant Isolation (WO-KBCV-T1-20260711)

- **Status**: CLOSED — Gate 1 remediation reviewed and committed
- **Date**: 2026-07-11
- **Phase**: FREEZE
- **Risk Level**: R2

### What was done (T1)

| Task | Status |
|------|--------|
| T1 — ADR and Identity Model | ✅ DONE — `docs/ADR-002-SESSION-DESIGN.md`, added `organization_id` & `is_active` to `User` |
| T2 — Secret and Login Hardening | ✅ DONE — fail-fast key check, timezone-aware expiry, IP-based login rate limit, admin bootstrap script |
| T3 — Server-side Authorization | ✅ DONE — role verification, tenant isolation ownership checks, workflow actor derived from JWT, ADMIN workflow lock |
| T4 — Data Migration (Alembic) | ✅ DONE — initialized Alembic, custom batch migration for SQLite, upgrade/downgrade rehearsal |
| T5 — Frontend Contract | ✅ DONE — loaded user from `/api/auth/me`, logout button, removed client actor name/role input, role-aware UI toggles |
| T6 — Security Tests | ✅ DONE — matrix-driven tests in `tests/test_rbac.py` + updated T0 suite to use role headers |
| T7 — Documentation and Handoff | ✅ DONE — updated `docs/API_CONTRACT.md`, created `docs/SECURITY_BOUNDARY.md` and `docs/USER_BOOTSTRAP.md`, generated Web Evidence Bridge |

### Test results (Gate 1 verification)

```
44 passed, 0 failed — reviewer re-run
Python 3.13.12 | pytest 8.2.0
```

### Reviewer remediation record (2026-07-11)

- The initial T1 closure was reopened because `git diff --check` failed and
  security/migration evidence was incomplete.
- Removed client-required workflow actor fields; actor identity is now solely
  derived from the authenticated server-side user.
- Added negative tests for tenant-scoped declaration lists, suggestions, crew
  updates, report output, invalid roles and expired tokens.
- Added an isolated Alembic upgrade/downgrade rehearsal against a legacy SQLite
  schema; unbound legacy non-admin users are disabled on upgrade.
- Reconciled API contract and security documentation with actual roles and the
  24-hour default token lifetime.
- Formatted all T1 files so `git diff --check` passes.

Final reviewer evidence after remediation:

- `pytest -q`: 44 passed, 0 failed.
- `git diff --check HEAD~1`: PASS.
- CVF Workspace Doctor: PASS 17/17.
- No runtime database, attachment, secret or raw token staged.

### Next governed move

**T2 — Domain Integrity and Persistence** is the next authorized design target.
Work order `WO-KBCV-T2-20260711` is READY FOR ASSIGNMENT but requires human R2
approval before BUILD. T3–T5 are PLANNED behind their preceding gates. T6 is
BLOCKED until official external authority prerequisites are available.

Issued work orders:

- `docs/WORK_ORDER_T2_DOMAIN_INTEGRITY_PERSISTENCE.md`
- `docs/WORK_ORDER_T3_FILES_IMPORTS_REPORTS.md`
- `docs/WORK_ORDER_T4_OPERABILITY_PRODUCTION_FOUNDATION.md`
- `docs/WORK_ORDER_T5_PRODUCT_PROFESSIONALIZATION.md`
- `docs/WORK_ORDER_T6_EXTERNAL_AUTHORITY_INTEGRATIONS.md`

### Human review closure record

1. ✅ Tests: `44 passed, 0 failed`
2. ✅ Gate 1: tenant isolation, RBAC matrix, Rate limit, and token validation PASS (verified by test suite)
3. ✅ Frontend user display, role constraints, and logout integration PASS
4. ✅ Database migrations (Alembic) upgrade and downgrade PASS in isolated automated rehearsal
5. ✅ CVF doctor re-run: PASS 17/17
6. ✅ Workspace Web Evidence Bridge generated PASS
7. ✅ Security and user bootstrap docs created PASS

---

## Tranche: T2 Domain Integrity and Persistence (WO-KBCV-T2-20260711)

- **Status**: CLOSED — Gate 2 reviewer evidence complete
- **Phase**: REVIEW
- **Risk Level**: R2

### What was done

- Removed runtime `create_all()` from the FastAPI application.
- Added Alembic baseline/T2 migration chain for fresh and legacy SQLite paths.
- Added optimistic versions to vessel, crew and declaration aggregates.
- Added correlation id propagation and authoritative audit metadata.
- Added transaction rollback in database dependencies and expanded regression
  coverage for stale updates, audit metadata and fresh/legacy migration paths.
- Standardized database constraint conflicts as `409 Conflict` and proved that
  a failed vessel write rolls back an organization created in the same request.
- Added Pydantic v2 model cleanup, validation boundaries, SQLAlchemy domain
  relationships and CHANGES_REQUESTED resubmission state reset.
- Connected optimistic versions to frontend edit requests.

### Gate 2 evidence

- Tests: `50 passed, 0 failed`.
- Fresh database migration to head: PASS.
- Legacy T0/T1 SQLite migration upgrade/downgrade rehearsal: PASS.
- Atomic rollback, stale-write conflict, workflow transition/resubmission and
  audit correlation tests: PASS.
- `git diff --check`: PASS.
- CVF Workspace Doctor after core reconciliation: PASS 17/17.
- Closure commits: `aa4c609`, `1b48cd5`, `0b80908`; manifest pin refresh is
  committed with this closure record.

### Next governed move

T3 — Files, Imports and Reports is now eligible for R2 BUILD approval. T4/T5
remain gated by their preceding work orders; T6 remains externally blocked.

---

## Tranche: T3 Files, Imports and Reports (WO-KBCV-T3-20260711)

- **Status**: CLOSED — local/pilot Gate 3 PASS
- **Phase**: REVIEW
- **Risk Level**: R2

### Work started

- Added fail-closed XLSX archive/XML limits: size, entry count, compression
  ratio, encrypted/path traversal entries, DTD/entity, external relationships,
  shared strings and cells.
- Attachment validation now rejects unsupported extensions before storage.
- Added regression fixtures for external relationship and compressed-bomb shapes.

### Completed after initial checkpoint

- Import preview, mapping/template version and idempotency evidence.
- Attachment quarantine/scanner adapter and local storage boundary.
- Golden-file report mapping review.
- Large-export asynchronous execution is deferred to T4 capacity work because
  the local pilot has no approved threshold or staging load profile.

### Gate 3 closure evidence

- Status: CLOSED for local/pilot scope.
- Approved mapping: `docs/REPORT_MAPPING_SPEC.md`.
- Golden dataset: `docs/REPORT_GOLDEN_DATASET.md`.
- Import preview, mapping version, SHA-256 idempotency and partial acceptance:
  implemented and tested with repository templates.
- Attachment checksum, quarantine storage and fail-closed scanner boundary:
  implemented; files remain QUARANTINED until a scanner is configured.
- Malicious XLSX/archive boundary tests: PASS.
- Tests: 58 passed, 0 failed.
- `git diff --check`: PASS.
- CVF Workspace Doctor: PASS 17/17.

### Next governed move

T4 local implementation is eligible. Production Gate 4 remains unavailable
until hosting/domain/staging owners are assigned.

---

## Tranche: T4 Operability and Production Foundation

- **Status**: LOCAL_GATE_PASS
- **Phase**: REVIEW
- **Risk Level**: R2

### Local evidence

- GitHub Actions quality workflow: format, compile, test and secret-pattern gate.
- Structured rotating local JSON logs and `/api/ready` database readiness check.
- Local SQLite backup, checksum manifest, integrity check, restore tool and
  30 daily/12 monthly/1 annual retention tooling.
- MinIO/S3-compatible adapter is opt-in through environment configuration;
  default remains local quarantine storage.
- ADMIN operations dashboard covers operations, workflow, fleet, imports,
  backup/storage and security aggregates.
- Tests: 63 passed, 0 failed; Doctor: PASS 17/17.

### Production blockers retained

- Hosting, domain, TLS/reverse proxy and staging environment.
- Real MinIO endpoint/secret provisioning, email/Teams configuration.
- Staging migration/smoke/rollback and real restore drill under named owners.

### Next governed move

T5 product professionalization may begin in local scope. T6 remains manual
adapter-ready; external activation remains blocked.

---

## Tranche: T5 Product Professionalization

- **Status**: IN PROGRESS — local accessibility/architecture baseline
- **Phase**: BUILD
- **Risk Level**: R1 (escalate to R2 for role or workflow semantic changes)

### Local checkpoint

- Recorded `docs/ADR-003-FRONTEND-ARCHITECTURE.md`: retain modular Vanilla JS
  for the pilot; a framework migration needs a separately approved plan.
- Added keyboard skip navigation, route focus management, visible focus,
  screen-reader status regions and dashboard `aria-busy` feedback.
- Static frontend assertions cover these accessibility hooks.
- Added compatible opt-in pagination for declarations: scope-safe filters,
  bound 1–100 page sizes, allowlisted ordering and URL-preserved filter/page
  state in the UI.
- Added a server-calculated, role-scoped attention queue to the dashboard;
  it displays only statuses visible to that role and never grants an action.
- Standardized write-form busy/recovery states and assertive API-error
  announcements to avoid duplicate submissions and inaccessible failures.
- Added `docs/T5_GATE5_EVIDENCE_PROTOCOL.md` for controlled UAT,
  accessibility, responsive and performance evidence collection.
- CVF public core reconciled at `141031c`; Workspace Doctor: PASS 17/17.
- Added audited, user-controlled in-app certificate-reminder preferences;
  fresh SQLite Alembic upgrade through `f05f0f000005` rehearsal: PASS.
- Tests: `66 passed, 0 failed`; `git diff --check`: PASS; CVF Doctor: PASS 17/17.

### Open Gate 5 evidence

Representative-user task study, browser-assisted accessibility audit,
responsive viewport matrix and reference-dataset performance measurements are
not yet available. Gate 5 is not closed.
