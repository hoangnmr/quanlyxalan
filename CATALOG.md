# Technical Catalog — Quan-Ly-Xalan

> Single entry point for understanding this codebase's architecture and finding
> the right file fast. Read this first; drill into the linked docs for detail.
> Snapshot date: 2026-07-25 (port operations section added; other sections not
> re-audited beyond what port operations touched). Line numbers are anchors,
> not contracts — if a grep doesn't match, the file moved; trust the code over
> this document.

## 1. What this system is

A FastAPI + vanilla-JS web app for multiple ports/reporting units. Customers
submit vessel declarations (a single declaration records both the ETB/ATB
arrival leg and the ETD/ATD departure leg — there is no separate "arrival
declaration" vs "departure declaration"); port staff either request changes
or approve them. Once approved, two port-side staff functions take over:
Bảo vệ (SECURITY) records actual ATB/ATD and confirms berth-fee collection,
Giao nhận (CARGO_OPS) confirms unload/load — gated so cargo confirmation
can't happen before the berth fee is confirmed. The platform produces the
periodic Appendix 1/2/3 reports required by the Maritime Administration
(Cảng vụ), and also imports audited historical TOS workbooks, reconciles
Berth/cargo/legacy PL.03 sources and reconstructs PL.03 without mutating live
declarations.

## 2. Runtime topology

```text
Browser (frontend/, static, no build step)
  -> /api/*  (fetch, JWT bearer)
backend/app.py            FastAPI app + ~90% of routes
  -> backend/database.py  SQLAlchemy engine/session, PostgreSQL (DATABASE_URL)
  -> alembic/              schema migrations (source of truth; app never create_all()s in prod path)
  -> backend/xlsx_io.py    stdlib+openpyxl XLSX import/export (reports, registers)
  -> backend/historical_api.py  APIRouter for the historical/TOS workbook import subsystem
```

Local/pilot mode: the FastAPI process also serves `frontend/` as static files.
Production: a reverse proxy serves `frontend/` and proxies `/api/` to Python.
Full detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 3. Stack at a glance

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | FastAPI | single app in `backend/app.py` |
| ORM / DB | SQLAlchemy + PostgreSQL (psycopg 3) | `backend/database.py`, `backend/models.py` |
| Migrations | Alembic | `alembic/versions/` — 16 revisions, T0→T6 progression + port operations |
| Validation | Pydantic v2 | `backend/schemas.py` |
| Auth | JWT bearer, local session | `backend/auth.py`, [docs/ADR-002-SESSION-DESIGN.md](docs/ADR-002-SESSION-DESIGN.md) |
| Frontend | Vanilla JS, single file, no framework/build | `frontend/app.js` (3325 lines), [docs/ADR-003-FRONTEND-ARCHITECTURE.md](docs/ADR-003-FRONTEND-ARCHITECTURE.md) |
| File storage | Local disk or MinIO (env-toggled) | `backend/storage.py` |
| XLSX import/export | Hand-rolled stdlib + openpyxl, zip-bomb guarded | `backend/xlsx_io.py`, `backend/historical_tos_parser.py` |
| Tests | pytest + httpx TestClient | `tests/` (4034 lines total) |
| Governance | CVF framework (phase-gated, work orders) | `AGENTS.md`, `.cvf/`, `docs/WORK_ORDER_*.md` |

## 4. Repository map

| Path | Purpose |
|---|---|
| `backend/` | All Python application code (FastAPI app, models, business logic) |
| `frontend/` | Static SPA: `index.html`, `app.js`, `styles.css`, `preview.html` (design preview) |
| `alembic/` | DB migrations — authoritative schema history |
| `docs/` | Architecture, ADRs, work orders, specs, audit/evidence records (see §9) |
| `scripts/` | Ops scripts: bootstrap, seed, backup/restore, appendix fixture generation |
| `tests/` | pytest suite, one file per subsystem |
| `templates/` | Reference/blank XLSX and DOCX templates the export logic must match |
| `knowledge/` | Markdown fed into CVF-governed AI runs (not app runtime knowledge) |
| `outputs/` | Generated review/audit artifacts from `scripts/generate_appendix_*` runs |
| `data/` | Attachments, backups — git-ignored |
| `.cvf/` | CVF governance manifest + policy (phase model, risk rules) |
| `.agents/`, `.codex/` | Other agent-tooling config, not app code |

## 5. Backend module catalog (`backend/`)

| File | Lines | Responsibility |
|---|---|---|
| `app.py` | 5041 | FastAPI app instance + nearly all HTTP routes (see §6 for the route index) |
| `models.py` | 737 | SQLAlchemy ORM models — every table (see §7) |
| `xlsx_io.py` | 923 | XLSX read/write: vessel/crew/register import, Appendix 1/2/3 export, zip-bomb guards |
| `historical_api.py` | 912 | `APIRouter` for historical/TOS preview, reconciliation, revision, confirmation, vessel links and synthesized PL.03 export |
| `historical_tos_parser.py` | 457 | Memory-bounded, filename-independent parser for audited historical TOS workbooks; never mutates source, keeps cell-level provenance |
| `tenant.py` | 185 | Shared tenant-scope guard (`CUSTOMER` vs `PORT` scope); every route resolving a reporting unit should depend on this instead of re-deriving checks |
| `historical.py` | 177 | Fail-closed tenant validators specific to historical import (multi-hop checks Alembic FKs can't express alone) |
| `schemas.py` | 134 | Pydantic request/response models |
| `database.py` | 100 | Engine/session factory, `get_db()`, PostgreSQL URL validation, `audit()` helper, cargo/TEU math, correlation-id context var |
| `auth.py` | 81 | JWT issuance/validation, `get_current_user` dependency |
| `integrations.py` | 83 | External maritime-authority adapter boundary — `MANUAL` mode only, no network calls until an official contract exists |
| `storage.py` | 75 | `ObjectStorage` protocol; local-disk and quarantine storage backends |
| `rbac.py` | 67 | Role enum (`CUSTOMER`, `PORT_STAFF`, `PLATFORM_ADMIN`), `require_roles()` / `RoleChecker`, `verify_organization_ownership()` |
| `logging_config.py` | 32 | Logging setup |

**Note on scale**: `app.py` at 3656 lines is a known hotspot — it holds nearly
every route handler. There's no per-domain router split yet (historical import
is the one exception, factored into `historical_api.py`). When adding routes,
grep the route index in §6 for the nearest neighbor rather than scanning the
whole file top to bottom.

## 6. API route index (grouped, from `backend/app.py` unless noted)

| Group | Method + path | Line |
|---|---|---|
| Auth | `POST /api/auth/login` | 545 |
| Auth | `GET /api/auth/me` | 607 |
| Auth | `POST /api/auth/logout` | 620 |
| Notifications | `GET/PUT /api/notification-preferences` | 634, 639 |
| Health | `GET /api/health`, `GET /api/ready` | 665, 670 |
| Catalogs | `GET /api/catalogs` | 684 |
| Orgs | `GET /api/organizations` | 700 |
| Admin | `GET /api/admin/operations-summary` | 709 |
| Admin/Backup | `GET/POST /api/admin/backups` | 761, 776 |
| Dashboard | `GET /api/dashboard` | 943 |
| Reporting units | `GET/POST /api/reporting-units` | 1078, 1103 |
| Reporting units | `GET /api/reporting-unit/organizations` | 1138 |
| Vessels | `GET /api/vessels`, `POST /api/vessels` | 1154, 1364 |
| Port register | `GET /api/port-vessel-register` (+`/export`) | 1180, 1226 |
| Port register | `POST /api/port-vessel-register/remove` `/add` | 1273, 1322 |
| Vessels | `POST /api/vessels/{id}/verify-registry` | 1465 |
| Crew | `GET/POST /api/crew` | 1515, 1529 |
| Declarations | `GET/POST /api/declarations` | 1615, 1685 |
| Declarations | `GET /api/declarations/{id}/events` | 1860 |
| Workflow | `POST /api/declarations/{id}/workflow` — incl. admin-only `CANCEL_FROM_PENDING`/`CANCEL_FROM_APPROVED` | 1889 |
| Attachments | `POST /api/declarations/{id}/attachments` | 1937 |
| Suggestions | `GET /api/suggestions` | 1990 |
| Import | `POST /api/import/port-vessel-register` `/vessels` | 2081, 2082 |
| Import | `POST /api/import/crew` | 2370 |
| Import | `POST /api/import/declaration` | 2535 |
| Reports | `GET /api/reports/analytics` (+`/export`) | 3057, 3072 |
| Reports | `GET/POST /api/reports/appendix2/adjustments` | 3399, 3421 |
| Reports | `GET /api/reports/{kind}` — Appendix 1/2/3 export | 3456 |
| **Port operations** | `POST /api/declarations/{id}/atb-atd` — Security/Cargo/Admin overwrite ATB/ATD | 2982 |
| " | `POST /api/declarations/{id}/berth-fee` — Security/Admin confirm berth fee | 3023 |
| " | `POST /api/declarations/{id}/cargo-ops` — Cargo/Admin confirm unload/load (hard-gated on berth fee) | 3064 |
| " | `GET /api/work-schedule` — cross-staff overview of in-cycle calls | 3108 |
| " | `POST /api/declarations/{id}/cancel-request` `/reject` — non-admin cancel request + Admin approve/reject | 3152, 3201 |
| Integrations | `GET /api/integrations/maritime-authority` | 3567 |
| Integrations | `POST /api/integrations/prepare-sync` | 3597 |
| **Historical import** (`backend/historical_api.py`) | `POST /preview` | 377 |
| " | `GET ""`, `GET /{import_id}` | 435, 665 |
| " | `POST /reconcile` | 467 |
| " | `GET /exports/pl03` | 637 |
| " | `GET /{import_id}/rows`, `/vessel-links` | 683, 728 |
| " | `POST /{import_id}/cancel` `/confirm` | 772, 797 |
| " | `POST /{import_id}/vessel-links/{link_id}/resolve` | 850 |

Full request/response shapes: [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## 7. Data model (`backend/models.py`)

| Group | Tables |
|---|---|
| Identity & tenant | `users`, `organizations`, `reporting_units`, `reporting_unit_users`, `reporting_unit_organizations`, `reporting_unit_vessels` |
| Core domain | `vessels`, `vessel_operating_profiles`, `declarations`, `crew_members`, `declaration_crew`, `attachments` |
| Workflow / audit (append-only) | `declaration_events`, `audit_events` |
| Reporting | `report_adjustments` (Appendix 2 manual adjustments) |
| Integrations | `integration_connectors`, `sync_jobs` |
| Imports (live data) | `import_jobs` |
| Historical/TOS import | `historical_report_imports`, `historical_report_rows`, `historical_report_metrics`, `historical_port_calls`, `historical_cargo_rows`, `historical_vessel_links` |

Canonical entity ownership, read paths and inheritance rules (which source
wins when data conflicts): [docs/DATA_INDEX.md](docs/DATA_INDEX.md),
[docs/DATA_FIELD_CATALOG.md](docs/DATA_FIELD_CATALOG.md),
[docs/DATA_INHERITANCE_RULES.md](docs/DATA_INHERITANCE_RULES.md),
[docs/DATA_PLATFORM_README.md](docs/DATA_PLATFORM_README.md).

**Port operations columns on `declarations`** (added without new tables —
see [ROADMAP_PORT_OPERATIONS.md](ROADMAP_PORT_OPERATIONS.md)): reuses the
pre-existing `actual_arrival_at`/`actual_departure_at` columns for ATB/ATD
(no new time columns); adds `berth_fee_status` + `berth_fee_confirmed_at` +
`berth_fee_confirmed_by_user_id`, `unload_status`/`load_status` +
`unload_is_adhoc`/`load_is_adhoc`, and `cancel_requested_at` +
`cancel_requested_by_user_id`. `reporting_unit_users` gained
`staff_function` (`SECURITY`/`CARGO_OPS`/`NULL`), scoped per membership row
so one person can hold different functions at different ports.

## 8. Auth, RBAC & tenant isolation

- **Roles** (`backend/rbac.py`): exactly `CUSTOMER`, `PORT_STAFF`,
  `PLATFORM_ADMIN`. There is no tenant-local `ADMIN`. `require_roles(...)` is
  the route-level gate.
- **Tenant scope** (`backend/tenant.py`): a request is either `CUSTOMER` scope
  (own `Organization`, no header needed) or `PORT` scope (`PORT_STAFF` /
  `PLATFORM_ADMIN` acting on one explicit reporting unit passed via the
  `X-Reporting-Unit-ID` header). `PORT_STAFF` needs an FK-backed membership row
  in `reporting_unit_users`; `PLATFORM_ADMIN` just needs the header. This is
  the dependency every new tenant-scoped route should use — don't hand-roll
  org/unit checks.
- Platform-wide operations (backups, reporting-unit creation and integrations)
  have separate `PLATFORM_ADMIN` gates. Tenant operations still require an
  explicit reporting-unit context.
- Threat model and boundary details:
  [docs/SECURITY_BOUNDARY.md](docs/SECURITY_BOUNDARY.md).

## 9. Reporting subsystem (Appendix 1/2/3)

- Appendix 1 and Appendix 3 start from the canonical Salan/register scope and
  populate activity from approved declarations; Appendix 2 provides monthly
  and YTD aggregates by cargo category, calls and passengers.
- Appendix 2 adjustments are reasoned deltas with audit provenance; they do not
  rewrite the source declaration.
- Export logic lives in `backend/xlsx_io.py`; route is
  `GET /api/reports/{kind}` (`app.py:3456`).
- Field-level mapping spec: [docs/REPORT_MAPPING_SPEC.md](docs/REPORT_MAPPING_SPEC.md).
- Verification dataset: [docs/REPORT_GOLDEN_DATASET.md](docs/REPORT_GOLDEN_DATASET.md).
- Reference workbook shapes the exporter must match: `templates/*.xlsx`.

## 10. Historical / TOS import subsystem

A separate subsystem for importing pre-existing port-call workbooks without
touching live operational data:

- `backend/historical_tos_parser.py` — parses the workbook, read-only, keeps
  per-cell provenance.
- `backend/historical_api.py` — preview, confirm/cancel, order-independent
  reconciliation, explicit revision decisions, vessel-link resolution and
  synthesized PL.03 export (routes in §6).
- `backend/historical.py` — fail-closed cross-tenant validators specific to
  this store.
- Source authority is explicit: Berth owns ATB/ATD and berth; cargo detail owns
  weight, TEU, movement and trade; legacy PL.03 is a static vessel-information
  fallback and cannot overwrite TOS time.
- Workbook type detection uses sheet/header structure, not the filename. Files
  may be selected together or confirmed in any order; a later confirmation
  triggers reconciliation of related imports in the same unit/period.
- Frontend: historical import workspace in `frontend/app.js` (~1433–1901).
- Audit trail of how this subsystem was scoped:
  [docs/HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md](docs/HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md),
  [docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md](docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md).

## 11. Frontend (`frontend/app.js`, single file, 3325 lines)

No framework, no build step, no modules — one script loaded by
`index.html`. Navigate by function name (`grep -n "^async function\|^function "`),
grouped roughly in this order:

| Section (approx. lines) | Covers |
|---|---|
| 1–314 | `api()` wrapper, session helpers, reporting-unit context and `route()` |
| 315–672 | Dashboard, vessel/declaration/crew lists and shared form helpers; cancel-request queue widget (`renderCancelQueue`, 493) lives here alongside the dashboard, not with the rest of port-ops |
| 673–1036 | Declaration wizard, port register, workflow actions, port-ops panel (`renderPortOpsPanel` 909, `savePortOpsAtbAtd`, `confirmPortOpsBerthFee`, `confirmPortOpsCargo`), split workflow/port-ops timelines (`renderWorkflowTimelines`) |
| ~1500–1600 (approx.) | "Kế hoạch làm hàng" work-schedule tab (`loadWorkSchedule` 1560, `renderWorkSchedule`), plus `requestCancelDeclaration` |
| further on | Live operational import preview/confirm, historical/TOS import workspace, report export/analytics, backup/integration controls, app bootstrap — line ranges shifted from the old 2299-line snapshot; grep function names rather than trusting line numbers here |

`index.html` — page shell/layout; `styles.css` — all styling; `preview.html`
— standalone design preview, not served in the real flow. Rationale for
staying single-file: [docs/ADR-003-FRONTEND-ARCHITECTURE.md](docs/ADR-003-FRONTEND-ARCHITECTURE.md).

## 12. Database migrations (`alembic/versions/`, oldest → newest)

| Revision | Tranche | What it did |
|---|---|---|
| `b01f0f000001` | T0 | Schema baseline |
| `ad84e1157033` | T1 | User↔Organization binding |
| `c02f0f000002` | T2 | Integrity, audit, versioning (optimistic `version` columns) |
| `d03f0f000003` | T3 | Import idempotency |
| `e04f0f000004` | T3 | Attachment quarantine |
| `f05f0f000005` | T5 | Notification preferences |
| `g06f0f000006` | — | Port enterprise workflow |
| `h07f0f000007` | — | Crew birth date |
| `i08f0f000008` | — | Normalize crew roles |
| `j09f0f000009` | — | Vessel operating profiles |
| `k10f0f000010` | — | Port vessel register scope |
| `l11f0f000011` | — | Canonical report snapshots |
| `m12f0f000012` | — | Historical TOS import store |
| `n13f0f000013` | — | Reporting-unit vessels |
| `o14f0f000014` | — | Cross-import TOS links |
| `p15f0f000015` | — | Vessel category |
| `q16f0f000016` | — | Crew onboard count |
| `r17f0f000017` | — | Email notifications |
| `s18f0f000018` | — | App settings |
| `t19f0f000019` | — | Declaration ↔ reporting unit link |
| `u20f0f000020` | — | Port operations phase 1: berth-fee/cargo-ops/cancel-request columns + `staff_function`. **Not yet run against the real `cangvu` database** — idempotent (`ALTER TABLE IF NOT EXISTS`-style guards) but only exercised on a throwaway test DB so far. Whoever merges this into the branch that owns the real DB must run `alembic upgrade head` against a backup/staging copy first. |

Schema changes go through Alembic only; the app never calls `create_all()`
against a real database on startup.

## 13. Tests (`tests/`, pytest)

| File | Lines | Covers |
|---|---|---|
| `test_backend.py` | 2746 | Broad API surface — the main regression suite |
| `test_historical_import.py` | 862 | Historical/TOS import flow end-to-end |
| `test_rbac.py` | 768 | Role checks, tenant isolation, `require_roles` |
| `test_port_operations.py` | 663 | Port operations: ATB/ATD, berth-fee, cargo-ops `staff_function` gating, `CANCEL_FROM_*` admin-only gates, work-schedule filtering, cancel-request queue |
| `test_frontend_ux.py` | 204 | Frontend structural/UX assertions |
| `test_user_management.py` | 197 | User CRUD, role/membership management |
| `test_historical_tos_parser.py` | 111 | Parser unit tests |
| `test_reporting_unit_bootstrap.py` | 73 | `scripts/bootstrap_reporting_unit.py` |
| `test_operations.py` | 36 | Ops/admin endpoints |
| `test_integrations.py` | 27 | Integration adapter (manual mode) |
| `test_storage.py` | 23 | Storage backend protocol |

Run: `pytest -q` (see [README.md](README.md) for env setup). All tests must
pass before committing — this is a hard project rule, not a suggestion.

## 14. Scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `run-dev.sh` | Applies Alembic migrations, then starts uvicorn |
| `bootstrap_admin.py` | One-time `PLATFORM_ADMIN` user creation |
| `bootstrap_reporting_unit.py` | Idempotently bind a legacy single-port DB to one `ReportingUnit`; preview-only unless `--apply` |
| `seed_demo_data.py` | Seeds disposable demo data (sentinel org `DEMO-TANTHUAN-2026`); refuses to run if real data exists |
| `backup_local.py` / `restore_local.py` | PostgreSQL backup/restore via `pg_dump`/`pg_restore` with a SHA-256 manifest; restore requires explicit confirmation |
| `register-local-backup-task.sh` | Registers a launchd daily backup job (macOS) |
| `generate_appendix_operational_review.py` | Read-only Appendix export from the live local DB, for review |
| `generate_appendix_positive_fixture.py` | Generates isolated Appendix workbooks via an in-memory DB (never touches `data/cang_vu.db`) |

## 15. Configuration (`.env`, see `.env.example`)

| Var | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret — must be overridden in any non-throwaway run |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 1440 (24h) |
| `ALLOWED_ORIGINS` | CORS allowlist, comma-separated |
| `OBJECT_STORAGE_MODE` | `LOCAL` or `MINIO` (all `MINIO_*` vars required together) |
| `TEST_DATABASE_URL` | Auto-set by the pytest suite |

## 16. Docs map (`docs/`) — what to read for what

The `docs/` folder is large because this project runs under the CVF
governance framework (phase-gated work orders, ADRs, audit evidence). Rather
than duplicate it, here's what to open for each need:

| Need | Doc |
|---|---|
| Overall architecture narrative | `ARCHITECTURE.md` |
| Why FastAPI, migration boundary | `ADR-001-FASTAPI-MIGRATION.md` |
| Why JWT/local session design | `ADR-002-SESSION-DESIGN.md` |
| Why single-file vanilla-JS frontend | `ADR-003-FRONTEND-ARCHITECTURE.md` |
| Full request/response contract | `API_CONTRACT.md` |
| Threat model / security constraints | `SECURITY_BOUNDARY.md` |
| Deployment / prod boundary | `DEPLOYMENT.md`, `EA_EVALUATION_ROADMAP.md` |
| Canonical data ownership & field rules | `DATA_INDEX.md`, `DATA_FIELD_CATALOG.md`, `DATA_INHERITANCE_RULES.md`, `DATA_PLATFORM_README.md` |
| Appendix report field mapping | `REPORT_MAPPING_SPEC.md`, `REPORT_GOLDEN_DATASET.md` |
| Historical import scope/audit | `HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md`, `HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md` |
| External authority integration boundary | `EXTERNAL_ADAPTER_SPEC.md` |
| Admin/user bootstrap | `USER_BOOTSTRAP.md` |
| Demo data rules | `DEMO_DATA_POLICY.md` |
| Product/UX intent | `PRODUCT_DESIGN_HANDOFF.md`, `UX_*` files |
| Current tranche status / handoff | `AGENT_HANDOFF.md` + latest dated `AGENT_HANDOFF_*.md` |
| Roadmap history by tranche (T0–T6) | `WORK_ORDER_T0_BASELINE_RECOVERY.md` … `WORK_ORDER_T6_EXTERNAL_AUTHORITY_INTEGRATIONS.md` |

**Tranche status as of the most recent work orders**: T0–T3 CLOSED, T4
LOCAL_GATE_PASS (prod gate blocked on infra), T5 LOCAL SCOPE COMPLETE, T6
MANUAL SCAFFOLD COMPLETE (external integration activation deferred). Treat
this line as a snapshot, not a source of truth — check `AGENT_HANDOFF*.md` for
the current state before relying on it.

## 17. "I need to change X" quick index

| Task | Start here |
|---|---|
| Add/modify an API route | `backend/app.py` (§6 for nearest neighbor) + `backend/schemas.py` + update `docs/API_CONTRACT.md` |
| Add a DB column/table | `backend/models.py` + new Alembic revision in `alembic/versions/` |
| Change role/permission logic | `backend/rbac.py` (roles), `backend/tenant.py` (tenant scoping) |
| Fix/extend declaration review (`PENDING_REVIEW → CHANGES_REQUESTED/APPROVED`) | `app.py` workflow route (`app.py:1889`) + `models.DeclarationEvent` |
| Change an Appendix export | `backend/xlsx_io.py` + `docs/REPORT_MAPPING_SPEC.md` + matching `templates/*.xlsx` |
| Historical import bug | `backend/historical_api.py` / `historical_tos_parser.py` / `historical.py` + frontend `*Historical*` functions |
| Port operations (Bảo vệ/Giao nhận, hủy phiếu) | `app.py` §6 "Port operations" routes + `models.py` (declaration columns, `staff_function`) + `tenant.py` (`Scope.staff_function`) + frontend `renderPortOpsPanel`/`renderWorkSchedule`/`renderCancelQueue` in `app.js`; business decisions in [ROADMAP_PORT_OPERATIONS.md](ROADMAP_PORT_OPERATIONS.md) |
| Frontend page/view behavior | `frontend/app.js` — find via `route()` (~line 292) then the matching `render*`/`load*` function |
| Attachment storage/scanning | `backend/storage.py` |
| External maritime-authority sync | `backend/integrations.py` (still `MANUAL`-only by design) |
| Local backup/restore behavior | `scripts/backup_local.py`, `scripts/restore_local.py` |
| Seed/demo data | `scripts/seed_demo_data.py` + `docs/DEMO_DATA_POLICY.md` |

## 18. Governance note

This repo runs under the CVF framework. Before non-trivial work, an agent
should read `AGENTS.md` at the repo root — it defines phase gates
(`INTAKE → DESIGN → BUILD → REVIEW → FREEZE`), risk classification, and the
first-read document list. This catalog is a navigation aid, not a
replacement for that process.
