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

- **Status**: LOCAL SCOPE COMPLETE — Gate 5 evidence deferred
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

> Historical T5 checkpoint status. For the isolated Recovery UX branch, this
> gap was subsequently closed by full-flow evidence commit `3574128`; see the
> Recovery UX session handoff below. Production release readiness remains
> separate.

Representative-user task study, browser-assisted accessibility audit,
responsive viewport matrix and reference-dataset performance measurements are
not yet available. Gate 5 is not closed. Reopen T5 only when the product owner
schedules `docs/T5_GATE5_EVIDENCE_PROTOCOL.md`, supplies the agreed reference
conditions/results, or authorizes a UX change that affects authority/workflow
meaning. T6 remains manual-scaffold complete and reopens only on receipt of the
official authority prerequisites recorded in its work order.

---

## Tranche: T5 UX Remediation (WO-KBCV-T5-UXR-20260713)

- **Status**: SUPERSEDED BY RECOVERY UX CLOSED/PASS EVIDENCE
- **Phase**: REVIEW
- **Risk Level**: R1; escalate to R2 for authority, workflow or legal mapping
  changes

### Completed before recovery integration

- Independent heuristic review and evidence-response documents recorded.
- Wizard step controls converted to native keyboard-operable buttons with
  accessible names and current/locked state semantics.
- Local draft status states that data is stored on the current device, is not
  yet saved to the system and includes the local save time.
- Added static frontend UX regression tests.
- Reordered the owner-approved wizard flow to A -> B -> C/D -> E -> attachments
  -> F without changing legal section meaning.
- Added inline field and persistent form-level error recovery.
- Replaced the crew multi-select with a keyboard/touch checklist and repaired
  the prior-trip crew suggestion path.
- Added role dashboard layout and standardized terminology.

### Closure relationship

The original local T5 checkpoint left Gate 5 open. The isolated Recovery UX
branch subsequently incorporated the approved UX intent and supplied browser
evidence for the six-step flow. The canonical final state is recorded in the
Recovery UX and Recovery Data/Reporting tranches below. Production readiness
remains outside this closure.

---

## Session handoff: Recovery UX branch — 2026-07-13

- **Branch**: `recovery/frontend-baseline-20260712`
- **Implementation/evidence commits**: `0b2ba72`, `5e74643`, `7c5431d`, `a2b1ca0`, `82b81f9`, `3574128`
- **Status**: CLOSED — all browser findings and full six-step wizard UAT passed.
- **Gate 5 Status**: CLOSED (PASS)
- **Canonical session handoff**:
  `docs/SESSION_HANDOFF_RECOVERY_UX_20260713.md`
- **UX issue ledger**:
  `docs/UX_REEVALUATION_RECOVERY_BRANCH_20260713.md`

Tất cả các bước UAT Wizard 1-6 đã hoàn thành. Bằng chứng kiểm thử visual được
lưu tại `docs/evidence/recovery-ux-20260714/`. Analytics và production/staging
readiness vẫn là phạm vi riêng, không được suy diễn là đã đóng cùng UX Gate 5.

---

## Tranche: Recovery Data, Reporting and Sidebar — 2026-07-14

- **Branch**: `recovery/frontend-baseline-20260712`
- **Status**: CLOSED — corrective import and targeted browser/database evidence PASS.
- **Phase**: REVIEW
- **Risk Level**: R2 (import/data replacement and role-scoped reporting)

Implemented & Verified:

- Lower-left sidebar group for Import Excel and Báo cáo hoạt động Cảng.
- Footer role labels `User`, `Admin`, `Port staff` with account identity.
- Visible API preparation/readiness information; ADMIN-only mutation controls.
- Week/month/quarter/year approved-declaration analytics and XLSX export.
- Sentinel datamock auto-removal on first real create/import while preserving a
  CUSTOMER organization binding.
- Smart XLSX header/sheet detection with preview diagnostics and passive external
  link-path ignore; mapping version `KBCV-IMPORT-1.2`.
- Normalized scalar numeric cells containing multiple source values in commit `1a2ae22`, preserving original values in notes and hiding internal SQL errors. Commit `a9946cb` adds a distinct idempotent re-import state; assets are verified at `?v=1.1.2`.

Evidence available:

- `pytest -q`: 71 passed.
- `node --check frontend/app.js`: PASS.
- `git diff --check`: PASS.
- Browser/UAT evidence (2026-07-14): ALL PASSED. Đã kiểm thử và chụp ảnh đầy đủ UAT cho cả 3 role (CUSTOMER, PORT_STAFF, ADMIN) và 3 viewport (Desktop, Tablet, Mobile) cũng như cả 2 theme (Dark, Light).
- Retest corrective commit `a9946cb`: preview hiển thị dòng 15/TN-0963 và badge chuẩn hóa; import lần đầu đạt 39/0, không lộ SQL; re-import hiển thị trạng thái duplicate-safe riêng.
- Báo cáo chi tiết: [docs/BROWSER_EVIDENCE_DATA_REPORTING_SIDEBAR_20260714.md](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/BROWSER_EVIDENCE_DATA_REPORTING_SIDEBAR_20260714.md).
- Targeted evidence đã đủ: network response lần hai có `idempotent=true`; database giữ 39 phương tiện và 1 import job; TN-0963 có giá trị chuẩn hóa cùng notes nguồn. Biên nhận nằm trong `docs/evidence/data-reporting-sidebar-20260714/`.
- Tranche **Recovery Data, Reporting and Sidebar** được đóng **CLOSED / PASS** trong phạm vi local/pilot. Không suy diễn kết luận này thành production readiness hoặc bằng chứng governance AI.

---

## Final integration to main — 2026-07-14

- **Status**: CLOSED — recovery baseline integrated with the six local T5 commits from `main`.
- **Phase**: FREEZE for local/pilot scope.
- **Risk Level**: R2 (main-branch integration).
- Recovery frontend is canonical because it carries the approved workflow and
  completed browser evidence. The earlier T5 history and decisions remain in
  this handoff for traceability.
- Stale static assertions from the earlier frontend were reconciled with the
  approved confirmation language and recovery implementation.
- Final integration verification: `79 passed`; `node --check frontend/app.js`:
  PASS; `git diff --check`: PASS; no unresolved conflict markers.
- The local reference workbook remains untracked and is not part of the merge.
- Production deployment/readiness and external API activation remain outside
  this closure.

---

## Post-integration corrective: sidebar, search and Excel conflict handling — 2026-07-15

- **Status**: IN REVIEW — automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (explicit overwrite of existing imported records).

Implemented:

- Preserved flex layout for the Import Excel and Báo cáo hoạt động Cảng links;
  role visibility now uses `hidden` instead of overriding the links with
  `display: block`, so each icon remains to the left of its label.
- Isolated dashboard type-ahead from the full dashboard/admin refresh. Searches
  start at two characters, are debounced and ignore stale responses.
- Added the missing ADMIN backup list/create API used by the existing dashboard,
  removing the unrelated `Not Found` toast source.
- Advanced vessel import mapping to `KBCV-IMPORT-1.3`: imported text is Unicode
  normalized, uppercased and whitespace-collapsed; registration formatting and
  controlled vessel-type variants such as `công te nơ`/`côngtenơ` are
  canonicalized without guessing arbitrary vessel names.
- Duplicate registrations are previewed with field-level changes. The safe
  default keeps existing data; overwrite requires a separate button and browser
  confirmation before the API accepts `overwrite_existing=true`.

Verification:

- `pytest -q`: 82 passed.
- `node --check frontend/app.js`: PASS.
- `git diff --check`: PASS.
- Manual browser/visual review remains with the user and is not claimed here.

---

## Appendix export and vessel-list correction — 2026-07-16

- **Status**: IN REVIEW — automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (official report mapping and current register inheritance).

Implemented:

- Replaced the former generic Excel exports with the approved table structures:
  16 columns for PL.01, 16 columns for PL.02 and the original 35-column
  `templates/Phụ lục 3.xlsx` table for PL.03.
- Activity reports remain based on approved declarations. When registration
  numbers match, current static vessel data from Hồ sơ phương tiện / Sổ theo
  dõi Salan overrides stale declaration snapshot values. Multiple operating
  profiles retain all deadweight and cargo-capacity values.
- PL.02 now separates selected-period metrics from year-to-report-date
  cumulative metrics.
- Hồ sơ phương tiện now shows STT, paginates at 15 records per page, resets to
  page one on search and no longer displays the import-owner remark.

Verification:

- `pytest -q`: 93 passed.
- `node --check frontend/app.js`: PASS.
- `python -m compileall -q backend`: PASS.
- `git diff --check`: PASS.
- Workbook structure tests verify column counts, merged headers, template
  headers, approved-only mapping and Sổ theo dõi inheritance.
- Manual browser/Excel visual review remains with the user and is not claimed
  here.

---

## Port Salan register and multi-area capacity preservation — 2026-07-15

- **Status**: IN REVIEW — implementation and automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (schema migration and controlled overwrite import).

Implemented:

- Replaced the first-number-only import behavior for multi-area Salan records
  with normalized `vessel_operating_profiles`. Each activity area keeps its
  corresponding deadweight and cargo capacity; the legacy scalar fields retain
  profile 1 for compatibility with existing declarations and reports.
- Added Alembic revision `j09f0f000009`, tracking master name/phone fields and
  a data migration for existing vessels. Local SQLite was backed up to
  `data/backups/cang_vu-20260715-porter-register-pre-migration.db` and upgraded;
  integrity check returned `ok`.
- Added the role-limited `Sổ theo dõi Salan` tab for PORT_STAFF and ADMIN with
  all 14 operational workbook columns, search, manual add/edit, authenticated
  Excel export and access to the smart vessel import card.
- Advanced vessel import mapping to `KBCV-IMPORT-1.4`. Count mismatches between
  activity areas, deadweights and cargo capacities are preserved and surfaced
  as preview warnings instead of silently dropping values.
- The local source workbook `templates/DU_LIEU_SA_LAN_T7.26.xlsx` was used as
  read-only validation input. It remains untracked because it contains real
  operational contact data and is not a public template artifact.

Verification:

- A validated source row (name withheld from public documentation) parsed as two profiles:
  `VR-SI / 2723.79 / 2698.79` and `VR-SII / 2912.57 / 2887.57`.
- `pytest -q`: 88 passed.
- `node --check frontend/app.js`: PASS.
- Alembic upgrade/downgrade rehearsal: PASS.
- Manual browser/visual review remains with the user and is not claimed here.

---

## Separate customer vessel import from the internal Port register — 2026-07-15

- **Status**: IN REVIEW — implementation and automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (data-scope migration, role isolation and controlled overwrite import).

Corrected business interpretation:

- `Hồ sơ phương tiện khách hàng gửi` remains the proxy-entry path used when a
  customer asks the Port to import on their behalf. These records support the
  customer declaration flow and are not automatically classified as internal
  Port tracking records.
- `Sổ theo dõi Salan` is a separate internal scope for PORT_STAFF and ADMIN.
  It has its own import endpoint and `PORT_VESSEL_REGISTER` import-job type,
  while reusing the normalized vessel identity and multi-area operating
  profiles to avoid duplicate physical-vessel records.

Implemented:

- Added Alembic revision `k10f0f000010` with `is_port_tracked` and
  `port_tracking_updated_at`; CUSTOMER access to the internal register,
  internal import and internal manual-add mode is denied.
- Added a dedicated import control and preview dialog inside the left-side
  `Sổ theo dõi Salan` page. The generic Import Excel page now explicitly labels
  the old card as customer-supplied vessel data.
- Added leadership summary cards for tracked Salan, operating profiles,
  multi-area vessels, TEU capacity and certificate warnings, plus breakdowns
  by activity area and vessel purpose.
- Internal export includes only records classified in the Port register.
- Local SQLite was backed up before migration, upgraded to
  `k10f0f000010 (head)`, then the provided tracking workbook was re-imported
  through the dedicated endpoint: 47 accepted, 47 updated, 0 rejected;
  integrity check returned `ok`.

Verification:

- `pytest -q`: 90 passed.
- `node --check frontend/app.js`: PASS.
- Alembic upgrade/downgrade rehearsal and fresh-head assertions: PASS.
- Manual browser/visual review remains with the user and is not claimed here.

---

## Customer flow and crew ownership correction — 2026-07-15

- **Status**: IN REVIEW — automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (role boundaries, crew import and schema migration).

Implemented:

- CUSTOMER navigation is limited to Phiếu khai báo and Danh sách thuyền viên;
  the six-step wizard is also available to ADMIN for controlled manual entry.
- PORT_STAFF cannot manually create, edit or assign crew. Permanent vessel
  assignment was removed from the crew form and import path; crew selection is
  now made by the CUSTOMER for each declaration.
- Added optional `crew_members.birth_date` with Alembic revision
  `h07f0f000007` and replaced the crew table's vehicle column with date of birth.
- Added smart crew XLSX preview/import for PORT_STAFF and ADMIN. A file is
  limited to one known customer organization; matching uses CCCD/passport,
  certificate number, then name plus date of birth. Imports create or update
  crew records and always clear legacy vessel assignment.
- Simplified the sidebar identity display to one role pill while retaining the
  logout action.
- Locked the crew-role catalog across manual entry, wizard entry and XLSX import
  to Thuyền trưởng, Máy trưởng, Thuyền viên and Thuyền phó. Alembic revision
  `i08f0f000008` consolidates legacy roles into Thuyền viên.
- Rebalanced the crew modal into two columns with readable default typography
  and control height; other operational forms retain their existing sizing.
- Local SQLite was backed up before migration and upgraded to
  `i08f0f000008 (head)`.

Verification:

- `pytest -q`: 85 passed.
- `node --check frontend/app.js`: PASS.
- Alembic fresh-database head test includes `crew_members.birth_date`.
- Manual browser/visual review remains with the user and is not claimed here.

---

## End-user admin and controlled import correction — 2026-07-15

- **Status**: IN REVIEW — automated regression PASS; user visual review pending.
- **Phase**: REVIEW
- **Risk Level**: R2 (ADMIN declaration creation and cross-tenant import).

Implemented:

- ADMIN can open `+ Tạo phiếu`, use the complete declaration wizard and save a
  manually created declaration. Customer confirmation remains CUSTOMER-only.
- Restored the Phiếu khai báo Excel card for ADMIN, alongside Hồ sơ phương tiện
  and Thông tin thuyền viên. The backend binds an ADMIN import to the normalized
  company named in the workbook and preserves tenant-aware idempotency.
- Technical operations, security, import counters and SQLite backup filenames
  remain protected by ADMIN APIs but are no longer loaded into the end-user
  dashboard.
- Crew form now uses a balanced two-column grid while retaining the shared
  readable label font, input font and 38px control height.
- Desktop import cards use a three-column layout, collapsing to two and then one
  column at responsive breakpoints.

Verification:

- `pytest -q`: 86 passed.
- `node --check frontend/app.js`: PASS.
- `git diff --check`: PASS.
- Manual browser/visual review remains with the user and is not claimed here.

---

## Canonical data and appendix assurance roadmap — 2026-07-16

- **Status**: PLANNED / NOT STARTED — documentation handoff only.
- **Phase**: REVIEW; return to DESIGN before implementation.
- **Risk Level**: R2 (canonical data ownership, schema/import behavior,
  tenant-scoped inheritance and official report output).

Decision:

- Keep all current downstream evidence and QA artifacts unchanged.
- Use the operational database as the canonical system of record; use a
  README/index only as the discovery and governance control plane.
- Separate master data, approved event data and report aggregates. Static Salan
  records may populate static QA fields but must not fabricate activity facts.
- Implement shared, tenant-scoped projections so tabs inherit governed data
  instead of maintaining independent copies.
- Defer all mapping into CVF public core until downstream decisions and evidence
  are stable. Upstream work must run in a separate session rooted at
  `D:\UNG DUNG AI\TOOL AI 2026\Controlled-Vibe-Framework-CVF`.

Evidence now available:

- `docs/APPENDIX_TEMPLATE_AUDIT_20260716.md` — static template/code audit.
- `docs/APPENDIX_EXPORT_VERIFICATION_20260716.md` — generated-workbook and
  visual Spreadsheet verification.
- `docs/CVF_UPSTREAM_USE_CASE_CANONICAL_DATA_AND_APPENDIX_AUDIT_20260716.md` —
  sanitized upstream proposal.
- `docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md` — governed
  downstream execution order and gates.

Current report conclusion:

- Column counts, table mapping and static-data placement pass for PL.01,
  PL.02 and PL.03.
- Full template fidelity is not yet approved: PL.01/PL.02 title blocks are
  absent, PL.02 changes `tháng báo cáo` to `kỳ báo cáo`, and PL.03 omits the
  signature block after dynamic rows.
- No report code should be changed until these four Major items are resolved by
  a human decision or documented exception.

Not done in this handoff:

- No application code, schema, template, workbook or operational data was
  changed.
- No commit or publication was made.
- No file was written to the CVF core or any sibling repository.
- No production-readiness or CVF-governance-behavior claim is made.

Next governed move:

1. Review and decide the T0 report-intent questions in the roadmap.
2. Move the new tranche to DESIGN and draft the canonical data catalog, index,
   inheritance rules and machine-readable field manifest.
3. Obtain human approval at the design gate before schema/code work.
4. Complete downstream implementation and evidence before opening a separate
   CVF-core session for the upstream lesson.

---

## Canonical Field Mapping addendum — 2026-07-17

- **Status**: REVIEWED / DESIGN BLOCKERS RECORDED — no implementation started.
- **Phase**: REVIEW; next implementation tranche remains DESIGN.
- **Risk Level**: R2.

New evidence:

- Section 11 of `docs/APPENDIX_EXPORT_VERIFICATION_20260716.md` now maps all
  67 columns: PL.01 16, PL.02 16 and PL.03 35.
- Each mapping identifies static/activity/aggregate class, canonical source,
  fallback, read time, report condition, blank/conflict rule and concrete
  workbook evidence.

Code-confirmed blockers:

1. **MAP-01 — PL.01/H:** `_appendix1_rows` falls back from static
   `vessels.passenger_capacity` to activity `declarations.passenger_count`.
2. **MAP-02 — PL.01/K:** `_appendix1_rows` uses `destination_port` as the
   departure position even though destination and departure berth are distinct
   concepts.
3. **MAP-03 — PL.02/C:P:** report queries filter by `declaration_date` and
   aggregation initializes no-activity metrics as `0.0`; the operating-date
   precedence and blank-versus-zero rule require formal approval.
4. **MAP-04 — PL.03/AI:** `_appendix3_rows` writes `company_name` into the
   agent/operator column without a dedicated canonical field or confirmed
   equivalence.

Field/UI gaps recorded for DESIGN:

- ATA/ATD already exist in the schema but need a controlled UI/workflow for
  entry or confirmation.
- Arrival/departure berth, agent/operator snapshot/relationship and an explicit
  passenger-call classification require business approval and may require
  schema/UI additions.
- Missing values must remain blank; numeric zero is valid only when explicitly
  measured or recorded.

Roadmap impact:

- T0 now gates APPX-01 through APPX-04 and MAP-01 through MAP-04.
- T1 adopts the 67-column mapping as its baseline data contract.
- T2/T3 cover approved schema, provenance and UI/workflow gaps.
- T4 requires a positive `APPROVED` event dataset and Spreadsheet visual QA,
  including arrival, departure, cargo, empty TEU, passenger, ATA/ATD, berth,
  agent/operator and missing-versus-zero cases.

Boundary:

- No application code, schema, template, workbook or operational data was
  changed during this review.
- No CVF-core file was changed. Upstream transfer remains deferred to a
  separate session after downstream acceptance.

---

## Appendix business decision review — 2026-07-17

- **Status**: PARTIALLY RESOLVED — T0 remains open; no code authorized.
- **Phase**: REVIEW.
- **Risk Level**: R2.

Source and method:

- Read all 55 paragraphs in the local owner-response document `AI.docx` using the
  Documents skill runtime. The source has no tables, comments or tracked
  changes.
- `render_docx.py` was attempted but could not run because LibreOffice/`soffice`
  is unavailable. Visual page QA is therefore explicitly unverified.
- Created `docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md` with the full
  decision matrix, APPX/MAP disposition, field implications and minimal
  remaining questions.

Decisions recorded:

- APPX-01 through APPX-03 are closed as business decisions: PL.01/PL.02 should
  keep the complete form, and PL.02 must use `tháng báo cáo`.
- APPX-04 is closed by explicit exception: PL.03 does not require the signature
  block.
- MAP-01 is closed as a business decision: PL.01/H is design passenger
  capacity; PL.01/O is the actual crew/passenger count.
- ATA/ETA, ATD/ETD, `declaration_date` as creation date, current static master
  inheritance, blank no-data behavior, passenger-call counting with zero
  passengers and YTD-from-January-1 are recorded.

Open decisions:

- MAP-02 through MAP-04 remain partially resolved.
- MAP-05 is newly opened: the owner requests one PL.03 row per call, while the
  approved mapping spec/exporter use one row per cargo movement.
- PL.01 versus Salan-dashboard scope, official multi-month PL.02 shape,
  cross-month call counting, PL.03 AE/AF ownership, agent snapshot/default and
  template spelling still require owner confirmation.

Boundary and next move:

- No application code, schema, frontend, template or workbook was changed.
- Remain in REVIEW until the seven questions in Decision Register section 6 are
  answered and `REPORT_MAPPING_SPEC.md` is revised/approved.
- Only then transition to DESIGN. Do not begin implementation from this
  handoff alone.

---

## T0 closure and transition to DESIGN — 2026-07-17

- **Status**: T0 CLOSED — T1 DESIGN AUTHORIZED; BUILD NOT AUTHORIZED.
- **Phase**: DESIGN.
- **Risk Level**: R2.

Owner confirmations:

- PL.01 uses approved daily declarations. Sổ theo dõi Salan and its leadership
  dashboard/export are a separate internal Port-management product.
- PL.02 produces one official form per month: selected-month values plus
  January-through-selected-month cumulative values. The web also needs a
  separate analytical reporting dashboard.
- PL.03 produces one row per canonical Salan/vessel, aggregating eligible
  customer declarations instead of expanding one row per cargo item.
- PL.02 calls are counted by operating arrival. PORT_STAFF or PLATFORM_ADMIN in
  explicit port context may apply a
  controlled, reasoned and audited manual adjustment.
- PL.03 AE is working/cargo-working port; AF is next destination.
- PL.03/AI keeps `Đại lý PTND` and reports the customer-declared approved
  snapshot.
- Approved labels are `TEUs`, `TEUs Rỗng` and `Quá cảnh`.

Artifacts updated:

- `docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md` now closes all seven
  confirmations and APPX-01–04/MAP-01–05 business decisions.
- `docs/REPORT_MAPPING_SPEC.md` is advanced to `KBCV-REPORT-MAP-1.1`, status
  `BUSINESS RULES APPROVED; DESIGN DETAILS PENDING`.
- `docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md` closes T0
  and starts T1 DESIGN.

T1 must still define before BUILD:

- deterministic PL.03 aggregation for multiple cargo names, dates, ports and
  agents on one vessel row, with drill-down reconciliation;
- audited PL.02 manual-adjustment data and workflow;
- canonical new fields and source precedence;
- official-export versus analytical-dashboard projections;
- positive approved-event and Spreadsheet visual acceptance evidence.

Boundary:

- No application code, schema, frontend, template or workbook was changed.
- No commit or push was made.
- Do not start BUILD until the T1 data contract and acceptance-test plan receive
  human approval.

---

## Canonical report BUILD in progress — 2026-07-17

- **Status**: T1 CLOSED; T2/T3 BUILD IN PROGRESS; visual Spreadsheet gate pending.
- **Risk**: R2.
- **Authorization**: owner instruction `Tiến hành sửa`.

Implemented in the working tree:

- T1 canonical README, index, field catalog, inheritance rules and machine-readable manifest.
- Declaration snapshots `departure_berth`, `agent_ptnd_name`, `is_passenger_call`.
- Append-only PL.02 call-adjustment model/API with PORT_STAFF or explicit-context
  PLATFORM_ADMIN control, reason and audit event.
- Official operating-date filter (ATA→ETA / ATD→ETD); `declaration_date` removed from report-period fallback.
- PL.02 calendar-month + January-to-month aggregation and blank-when-absent behavior.
- PL.03 one row per canonical vessel, additive numeric aggregation and distinct chronological text aggregation.
- Full title/metadata/form blocks for PL.01 and PL.02; corrected `tháng báo cáo`, `TEUs`, `TEUs Rỗng`, `Quá cảnh`; PL.03 column-D clipping repair.
- Web month selector, controlled PL.02 adjustment panel and declaration inputs for the new snapshots.

Evidence:

- `python -m pytest -q`: 94 passed.
- Python compile, `node --check frontend/app.js` and `git diff --check`: passed.
- Local DB backed up to `data/backups/cang_vu-20260717-145400.db` with manifest, then migrated to `l11f0f000011`.
- Operational DB remains 47 vessels, 0 declarations, 0 approved declarations and 0 adjustments.
- Synthetic positive workbooks were generated at `outputs/appendix-positive-fixture-20260717/` without reading or mutating the operational DB.

Open gate:

- Browser interaction QA is blocked because the managed browser policy rejects localhost; only static frontend and API regression checks are complete.
- Run `docs/WORK_ORDER_CODEX_DESKTOP_SPREADSHEET_REGRESSION_20260717.md` in Codex Desktop. Do not close APPX/MAP implementation items until its artifact-tool renders pass.
- BUILD foundation was committed locally as `5db6022`; it has not been pushed.

### Owner clarification — canonical Salan row skeleton

After commit `5db6022`, the owner clarified that having zero approved
declarations must not remove the 47 known Salan rows from PL.01/PL.03.

- PL.01 and PL.03: start from canonical Salan master rows; populate every known
  static field; overlay activity only from `APPROVED` declarations; otherwise
  leave activity cells blank.
- PL.02: activity aggregate only; with zero approved activity, C:P remain blank.
- This supersedes the earlier interpretation that approval controlled the
  existence of the entire PL.01/PL.03 row. Approval controls activity only.
- Automated static-only coverage was added, and read-only operational review
  files contain 47 PL.01 rows, blank PL.02 metrics and 47 PL.03 rows.
- The updated Desktop work order now checks both the operational 47-Salan set
  and the isolated positive fixture before recommending tranche closure.

---

## PL.03 focused visual-regression follow-up — 2026-07-17

- Full Desktop Spreadsheet regression passed all zero-path and positive mapping
  checks but found one visual defect: `B/PL.03!AG10:AH10` clipped the second
  arrival/departure timestamp at the fixed 66-pt data-row height.
- The exporter now derives PL.03 data-row height from wrapped cell content;
  the positive fixture row is 108 pt while the FORM column widths and values
  remain unchanged.
- Automated evidence: targeted test PASS and complete suite `95 passed`.
- Regenerated workbooks are in `outputs/appendix-positive-fixture-20260717/`
  and `outputs/appendix-operational-review-20260717/`.
- Run
  `docs/WORK_ORDER_CODEX_DESKTOP_SPREADSHEET_REGRESSION_RECHECK_20260717.md`.
  Keep the Spreadsheet release gate OPEN until the focused artifact-tool render
  confirms `AG10:AH10` is fully legible and no PL.03 layout regression exists.
- Live business data evidence remains NOT PROVABLE because the operational DB
  still has no approved declarations; synthetic fixture PASS proves only the
  exporter implementation path.

---

## Canonical appendix implementation tranche closure — 2026-07-17

- **Status**: CLOSED / PASS for the approved local implementation scope.
- **Phase**: REVIEW; production/live-business readiness is not claimed.
- Codex Desktop used the required Spreadsheets runtime and artifact-tool to
  inspect both PL.03 workbooks and review seven renders.
- REG-01 is CLOSED. Positive PL.03 visual gate, operational 47-Salan guardrail
  and overall Spreadsheet implementation gate are PASS.
- APPX-01–04 and MAP-01–05 are CLOSED at implementation level. APPX-04 remains
  an approved no-signature exception.
- Application verification rerun: `python -m pytest -q` → `95 passed`.
- The local operational database still has zero approved declarations. Static
  Salan rows are valid; blank activity is expected. Live business data remains
  NOT PROVABLE until a real approved sample is reconciled.
- Evidence:
  `docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RECHECK_RESULT_20260717.md` and
  `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/`.
- No CVF-core change is authorized. T5 stays deferred to a separate session in
  the CVF repository.

---

## End-user live-data follow-up — 2026-07-17

- The implementation tranche remains CLOSED/PASS; a separate live-data
  acceptance gate is OPEN because the current DB has no approved declarations.
- Use `docs/LIVE_DATA_VALIDATION_AND_POST_PILOT_RUNBOOK_20260717.md` after end
  users have entered a small representative approved sample.
- Remaining evidence covers operating dates across months, real cargo
  classification, missing-versus-zero, berth/port/agent snapshots, PL.02 audit
  adjustments, multi-declaration PL.03 aggregation and tenant/role behavior.
- Diagnose source → workflow → canonical snapshot → projection → workbook
  before changing code. A fix requires a reproducible case, owner-confirmed
  expectation, regression test and renewed Spreadsheet render when applicable.
- Raw customer workbooks, DB snapshots and personal data must remain outside
  Git; commit only sanitized acceptance evidence.

---

## Historical appendix import workstream intake — 2026-07-17

- **Status**: INTAKE; BUILD NOT AUTHORIZED.
- Owner requires old PL.01/PL.02/PL.03 workbooks to populate a separate
  historical reporting store and dashboard, not to fabricate declarations.
- Roadmap:
  `docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md`.
- Historical facts remain separate from live `APPROVED` declarations and
  canonical masters. PL.02 month and YTD values must be stored separately;
  combined live/historical totals require explicit overlap resolution.
- Next move: provide at least one representative real workbook per appendix,
  then run full Spreadsheets skill inspection and close HDEC-01–HDEC-09 before
  schema or code work.

---

## Historical TOS workbook audit and owner time disposition — 2026-07-18

- **Status**: H0 AUDIT COMPLETE; H0 remains OPEN on owner decisions and missing
  historical PL.01/PL.02 samples. BUILD is not authorized.
- **Phase**: INTAKE; bounded H1 parser/data-contract DESIGN is eligible, but
  final H1 approval is not yet granted.
- Codex Desktop inspected five workbooks/six sheets read-only with the
  Spreadsheets skill and `@oai/artifact-tool`, covering 100% of used ranges
  across thirteen local renders. No workbook was modified and no raw render is
  committed.
- Evidence:
  `docs/HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md` and
  `docs/historical_tos_mapping_draft.json`.
- Verified sample facts: 40 Berth calls; 1,067 cargo rows across 38 detail call
  keys; all detail rows exact-match a Berth key; two Berth calls have no cargo.
  Salan linking produced 10 exact, 26 controlled-normalized, four unmatched
  and zero ambiguous candidates.
- Verified PL.03 mapping: B=`Tên PTTND`, AG=`Ngày đến cảng`, AH=`Ngày rời
  cảng`, AI=`Đại lý PTND`; historical and blank PL.03 variants share 35
  physical columns but differ in hidden state, data rows and footer position.
- Owner closed `TOS-PL03-TIME-01`: the supplied legacy PL.03 used inaccurate
  ETA-derived time. Matched TOS ATB/ATD are authoritative for reconstructed
  historical PL.01/PL.03; legacy AG/AH remain reported provenance only.
- Owner closed the remaining core TOS baseline: Detail/R is tonnes per
  container and both full/empty container weight contributes to report tonnes;
  F/E independently selects full/empty TEU columns. The four movement methods
  are approved as load/unload mappings.
- The legacy PL.03 is a non-authoritative manual summary and no longer blocks
  TOS parser design on 73-versus-40 row reproduction. Reporting month uses ATB;
  matched TOS wins actual time/berth/cargo while live retains declaration-only
  facts and the call counts once.
- Overlapping updated TOS imports require an explicit PORT_STAFF or
  explicit-context PLATFORM_ADMIN revision
  choice. Historical data/provenance/source receipt retention is at least five
  years, with user export as an additional copy channel.
- Owner closed HDEC-02 with a multi-port product decision. Cảng Tân Thuận is
  the first tenant, not a hardcoded boundary. Shared/versioned government PL
  report contracts use tenant-scoped data and identity; every import/report
  belongs to one authenticated reporting unit, and port/vendor TOS differences
  use versioned source adapters. Mixed-unit batches cannot commit silently and
  ordinary port roles cannot cross tenant boundaries.
- Historical PL.01/PL.02 variant audit is deferred until files are supplied.
  Historical label/coverage fixtures remain DESIGN items.
- Next governed move: draft the bounded H1 schema/parser/API/UI acceptance
  contract. Do not implement migration, parser, database import or dashboard
  before explicit BUILD authorization.

---

## Historical TOS H1 approval and BUILD transition — 2026-07-18

- **Status**: H1 APPROVED; H2 BUILD IN PROGRESS.
- **Risk Level**: R2; owner explicitly authorized the transition on 2026-07-18.
- Approved boundary: multi-port, tenant-isolated historical/TOS schema,
  migration, provenance, idempotency and acceptance-test foundation first;
  parser/API and UI follow the ordered roadmap gates.
- Cảng Tân Thuận remains the first tenant, not a hardcoded product boundary.
- Historical PL.01/PL.02 variants remain deferred. Unsupported layouts,
  labels, cargo classes and invalid-value paths must fail closed until covered
  by audited evidence or sanitized golden fixtures.
- Raw operational workbooks and renders remain outside Git.
- This transition does not authorize production deployment, external data
  transmission, or skipping REVIEW and FREEZE.
- Next governed move: commit the approved design checkpoint, then implement H2
  with migration upgrade/rollback, tenant-isolation, idempotency and audit
  tests before starting H3.

---

## Historical TOS H2 schema/migration/provenance BUILD — 2026-07-18

- **Status**: H2 IMPLEMENTED IN WORKING TREE — PENDING INDEPENDENT CODEX REVIEW.
  Not committed; not closed. No production readiness or governance-behaviour
  claim is made.
- **Phase**: BUILD (owner-authorized 2026-07-18). REVIEW and FREEZE gates remain
  ahead. H3/H4 not started.
- **Risk Level**: R2.

Implemented (schema/migration/provenance only — no parser, API or UI):

- Added six historical/TOS tables in `backend/models.py`:
  `historical_report_imports`, `historical_report_rows`,
  `historical_report_metrics`, `historical_port_calls`,
  `historical_cargo_rows`, `historical_vessel_links`.
- Multi-port tenancy reuses the existing Organization tenant table. Every
  historical table carries a non-null `reporting_unit_id` -> `organizations.id`;
  no second tenant system was introduced. Cảng Tân Thuận is a normal
  Organization row, not hardcoded in the schema.
- Idempotency is tenant-scoped: `uq_historical_import_idempotency` on
  `(reporting_unit_id, source_kind, source_checksum, mapping_version)`; port
  call / cargo source-row uniqueness is `(reporting_unit_id, import_id,
  source_sheet, source_row)`. Identical checksums/identities in different
  reporting units never collide.
- Revision lineage via self-referential `superseded_by_import_id` +
  `revision_no` + `supersede_reason`.
- Provenance preserved per fact: source sheet/row/cell, raw payloads, detected
  `mapping_version`, blank-vs-measured-zero `value_state`/`weight_state`, ATB
  kept as ATB (never renamed ATA), and observed misspelled headers retained.
- `historical_vessel_links` records reviewed candidate links only and has no
  authority to mutate canonical Vessel fields.
- Alembic revision `m12f0f000012` (revises `l11f0f000011`) creates the tables
  additively with guarded, idempotent upgrade and a reversible downgrade that
  drops only the new tables. It never alters existing declarations, vessels,
  crew or canonical masters.

Evidence:

- `python -m pytest -q`: 107 passed (96 baseline + 11 new in
  `tests/test_historical_import.py`).
- `python -m compileall backend`: PASS. `git diff --check`: PASS.
- Fresh-DB upgrade to `m12` head, upgrade→rollback→re-upgrade rehearsal and
  guarded-idempotent re-run: PASS (temp copies).
- Operational DB backed up to
  `data/backups/cang_vu-20260718-021834-pre-m12-historical.db`, rehearsed on a
  disposable copy (up→down→up), then upgraded to `m12` head:
  `PRAGMA integrity_check = ok`; 59 vessels and 0 declarations unchanged; the 6
  historical tables are empty (no historical data imported yet).
- New tests cover fresh head, upgrade/rollback preservation of the live domain,
  guarded upgrade idempotency, tenant-scoped checksum idempotency, cross-tenant
  isolation, per-import source-row uniqueness, revision lineage, blank-vs-zero,
  cascade delete of child facts, no-overwrite of the canonical vessel, and an
  audit event recorded for a historical import.

Boundary / not done:

- No parser, import API, dashboard or UI (H3/H4).
- No raw workbook, render or operational DB committed; `templates/*.xlsx` and
  `data/` remain untracked/gitignored.
- No CVF-core change. Upstream transfer stays in a separate session.

Next governed move:

- Independent Codex review of the diff, migration and tests. On acceptance,
  proceed to H3 (type/version detection and explicit PL.01/PL.02/PL.03 + TOS
  parsers with preview, provenance evidence and safe partial acceptance) behind
  its gate. Do not start H3 before H2 review passes.

---

## Historical TOS H2 correction round 1 — 2026-07-18

- **Status**: H2 CORRECTED IN WORKING TREE — PENDING CODEX REVIEW ROUND 2.
  Not committed; not closed; H3/H4 not started.
- **Phase**: BUILD. REVIEW and FREEZE gates remain ahead.
- **Risk Level**: R2.
- **Order**: executed `docs/CLAUDE_H2_CORRECTION_ORDER_20260718.md` (H2 REJECTED).

### Withdrawn claim

The earlier H2 checkpoint (section "Historical TOS H2 schema/migration/provenance
BUILD — 2026-07-18") asserted tenant isolation on the strength of passing tests.
**That tenant-isolation claim is withdrawn.** Codex reproduced that the original
design used `Organization` as the tenant (PORT_STAFF often has no
`organization_id`), relied on unrelated single-column foreign keys, and ran with
SQLite `PRAGMA foreign_keys = 0`, so declared foreign keys and cascades were not
enforced. Passing tests did not establish isolation.

### Corrections implemented (schema/migration/provenance only)

- **Distinct tenant entity.** Added `ReportingUnit` (`reporting_units`), a Port
  that operates the product, separate from customer `Organization`. Added a
  nullable `reporting_unit_id` to `organizations` and `users` (plain columns,
  no backfill; pre-H2 rows and platform admins stay NULL). Cảng Tân Thuận is not
  hardcoded, seeded or defaulted anywhere.
- **Composite-foreign-key tenant consistency.** Every historical child carries a
  composite FK onto `historical_report_imports(id, reporting_unit_id)` (and
  metric→row, cargo→call, link→call composites), so a child in unit B cannot
  reference a parent in unit A. Revision lineage uses a composite self FK, so a
  cross-unit supersession is rejected. Import identity/idempotency keys are
  tenant-scoped.
- **Real SQLite foreign keys.** `backend/database.py` enables
  `PRAGMA foreign_keys=ON` on every SQLite connection via a global connect hook
  (application, Alembic and test engines). Verified `PRAGMA foreign_keys = 1`
  and `PRAGMA foreign_key_check` clean on test databases.
- **Fail-closed cross-unit vessel link.** The multi-hop rule (link → vessel →
  organization → reporting_unit) is not portably a single DB constraint. The DB
  boundary is the plain `candidate_vessel_id` FK; `backend/historical.py`
  `validate_vessel_link_tenant` fails closed on a missing vessel, an unbound
  organization or a different unit. Documented limitation, with negative tests.
- **Migration m12 corrected.** The artificial stamp-back "idempotency" test was
  removed. The migration creates the exact approved schema and then runs a
  fail-closed `_verify_tenant_schema` that raises on any drifted/partial
  pre-existing schema (rebutting the silent-guard concern). One Alembic head.
  Upgrade/downgrade/re-upgrade rehearsed on disposable databases only; downgrade
  removes only the H2 tables and the two `reporting_unit_id` columns.
- **Provenance/CHECK constraints.** Added portable CHECKs: `revision_no >= 1`,
  non-negative counts and source size, `teu_factor IN (1,2)` or NULL, approved
  status/state value sets, and blank-vs-zero value/weight consistency. ATB and
  ATD remain separate facts; no ATA field is introduced; blank, zero and invalid
  remain distinct states.

### Migration-guard note (design decision for review)

The `b01` baseline migration builds current model metadata with
`Base.metadata.create_all`, so a fresh database already contains the H2 tables
before m12 runs (the same pattern `d03`/`e04`/`l11` rely on). Removing the
`_has_table` guards outright makes a fresh-DB upgrade fail with
"table already exists" (reproduced). m12 therefore keeps per-object guards for
baseline compatibility **and** adds a fail-closed post-verification of the
tenant-critical composite keys so a drifted schema aborts loudly rather than
being silently accepted. The legacy create path (no pre-existing H2 tables) is
covered by `test_pre_h2_database_preserved_through_migration`.

### Evidence actually exercised by tests

- `python -m pytest -q tests/test_historical_import.py`: 24 passed.
- `python -m pytest -q`: 120 passed (96 prior + 24 new).
- `python -m compileall backend` and the migration/test modules: PASS.
- `git diff --check`: PASS. One Alembic head: `m12f0f000012`.
- Fresh-DB upgrade to head, hand-built pre-H2 seed preserved through
  upgrade→downgrade→re-upgrade, `PRAGMA foreign_keys = 1`, and
  `PRAGMA foreign_key_check` clean: all asserted by tests on disposable DBs.
- Negative tests that perform a forbidden operation and assert
  `IntegrityError`/fail-closed validation: `test_duplicate_checksum_in_one_unit_rejected`,
  `test_tenant_isolation_row_cannot_reference_foreign_import`,
  `test_tenant_isolation_metric_cannot_reference_foreign_import`,
  `test_tenant_isolation_metric_cannot_reference_foreign_row`,
  `test_tenant_isolation_port_call_cannot_reference_foreign_import`,
  `test_tenant_isolation_cargo_cannot_reference_foreign_call`,
  `test_tenant_isolation_vessel_link_cannot_reference_foreign_import`,
  `test_tenant_isolation_revision_cannot_cross_units`,
  `test_vessel_link_requires_import`,
  `test_cross_unit_candidate_vessel_fails_closed`,
  `test_candidate_vessel_with_unbound_org_fails_closed`,
  `test_blank_metric_with_a_number_is_rejected` (12 total).
- Database-level cascade via direct SQL `DELETE` (not ORM cascade):
  `test_database_cascade_delete_via_direct_sql`.

### Operational database blocker (unchanged this turn)

```text
Operational DB is stamped with rejected m12 and requires a separate,
Codex-reviewed reconciliation step after the corrected migration is accepted.
```

`data/cang_vu.db` still carries the earlier rejected m12 schema (organization-based,
no `reporting_units`, single-column keys, `foreign_keys = 0`). It was **not
modified, downgraded, restored, stamped or migrated during this correction**
(read-only check only: version `m12f0f000012`, `foreign_key_check` clean, 59
vessels, 0 declarations). No backup database was modified.

### Boundary / residual limitations

- No parser, import API, dashboard or UI (H3/H4). Not started.
- `organizations`/`users.reporting_unit_id` are plain columns without an inline
  DB foreign key (SQLite cannot DROP a foreign-key column or rebuild these
  parent tables under enforced FKs with child rows), so their binding integrity
  is service-layer/fail-closed rather than DB-enforced. The historical store
  itself retains full composite-FK enforcement.
- Cross-reporting-unit candidate vessel linking is enforced by fail-closed
  service validation, not a single DB constraint (documented above).
- No raw workbook, render, database or backup committed; `templates/*.xlsx` and
  `data/` remain untracked/gitignored. No CVF-core change.

### Next governed move

- Codex review round 2 of the diff, corrected migration and tests. Do not commit,
  do not touch the operational DB, and do not start H3 before this review passes.

---

## Historical TOS H2 correction round 2 — 2026-07-18

- **Status**: H2 CORRECTED AGAIN IN WORKING TREE — PENDING CODEX REVIEW ROUND 3.
  Not committed; not closed; H3/H4 not started.
- **Phase**: BUILD. REVIEW and FREEZE gates remain ahead.
- **Risk Level**: R2.
- **Order**: executed `docs/CLAUDE_H2_CORRECTION_ORDER_R2_20260718.md`
  (H2 REJECTED AFTER REVIEW ROUND 2). The round-1 passing baseline
  (distinct `ReportingUnit`, historical composite FKs, SQLite FK enforcement,
  DB cascade, migration up/down/re-up) was preserved and not regressed.

### R2 blockers fixed

- **Soft tenant columns replaced with FK-backed memberships.** Removed
  `User.reporting_unit_id` and `Organization.reporting_unit_id` (they accepted
  nonexistent ids). Added `reporting_unit_users` and
  `reporting_unit_organizations` — composite-PK, many-to-many, both sides real
  FKs with `ON DELETE CASCADE`. A nonexistent user/organization/reporting-unit
  id now fails by foreign key. A user/org may belong to several ports; existing
  users/orgs get no memberships and none is backfilled to Cảng Tân Thuận.
- **Fail-closed actor/reviewer authorization** in `backend/historical.py`:
  `validate_import_actor` and `validate_reviewer`. PORT_STAFF and tenant-local
  ADMIN require membership in the target unit; CUSTOMER and inactive users are
  rejected; missing user/unit is rejected; a platform ADMIN with no membership
  is authorized ONLY with an explicit `platform_context=True`. Absence of
  membership never, by itself, grants access. These cover creation, revision
  selection and supersession actor decisions and manual-review reviewer checks.
- **Candidate-vessel membership validation.** `validate_vessel_link_tenant` now
  uses `reporting_unit_organizations` membership (not a soft column): a vessel is
  valid for any port in which its owning Organization holds a real FK-backed
  membership; missing vessel/organization or membership only in another port
  fail closed; an unresolved candidate stays allowed as pending.
- **Tenant-scoped audit.** Added a nullable `reporting_unit_id` FK to
  `audit_events`; `backend.database.audit` accepts an optional
  `reporting_unit_id` (backward compatible — existing callers unaffected).
  `organization_id` still means customer Organization and is never overloaded
  with a Port id. Nonexistent reporting unit is rejected by FK.
- **Complete schema-drift verification.** `_verify_tenant_schema` now checks the
  reporting-unit and both membership tables (composite PK + both FKs), import
  identity/idempotency keys, the import self-revision composite FK, every
  child→import composite FK, the metric→row / cargo→call / link→call composites,
  `historical_vessel_links.import_id` NOT NULL, the row/call identity keys, the
  critical status and blank/zero CHECK constraints, and the audit tenant FK. It
  fails with a precise, named message. A test builds a drifted schema missing the
  cargo→port-call composite and proves verification rejects it.

### Migration note

`m12` still keeps per-object `if not _has_table` guards because the `b01`
baseline runs `Base.metadata.create_all` (so a fresh DB already has these objects
before m12 runs); the guards are paired with the full fail-closed
`_verify_tenant_schema`, so a drifted/partial pre-existing schema aborts loudly.
`organizations`/`users` have no soft tenant column in either the model or the
migration. On downgrade the `audit_events.reporting_unit_id` FK column is removed
by rebuilding that (unreferenced) table via `batch_alter_table`; membership and
historical tables and `reporting_units` are dropped; live rows are preserved.

### Evidence actually exercised by tests (disposable DBs only)

- `python -m pytest -q tests/test_historical_import.py`: 47 passed.
- `python -m pytest -q`: 143 passed (96 prior + 47).
- `python -m compileall backend` and the migration/test modules: PASS.
- `git diff --check`: PASS. One Alembic head: `m12f0f000012`.
- Fresh-DB upgrade to head, hand-built pre-H2 seed preserved through
  upgrade→downgrade→re-upgrade (now including an `audit_events` row and the audit
  column add/remove), `PRAGMA foreign_keys = 1`, and `PRAGMA foreign_key_check`
  clean.
- **New negative tests (12)** that attempt a forbidden operation and assert
  `IntegrityError`/fail-closed: membership with nonexistent reporting unit
  (`test_membership_requires_existing_reporting_unit`), nonexistent user
  (`test_membership_requires_existing_user`), nonexistent organization
  (`test_org_membership_requires_existing_organization`); PORT_STAFF on foreign
  import (`test_import_actor_portstaff_on_foreign_unit_rejected`); tenant ADMIN
  on foreign import (`test_import_actor_tenant_admin_on_foreign_unit_rejected`);
  CUSTOMER actor (`test_import_actor_customer_rejected`); inactive actor
  (`test_import_actor_inactive_user_rejected`); platform ADMIN without context
  (`test_import_actor_platform_admin_without_context_rejected`); cross-port
  reviewer (`test_reviewer_cross_port_rejected`); candidate vessel with only
  another-port membership (`test_vessel_link_other_port_only_membership_rejected`);
  historical audit with nonexistent reporting unit
  (`test_audit_with_nonexistent_reporting_unit_rejected`); schema drift missing a
  secondary composite (`test_schema_drift_missing_secondary_composite_is_rejected`).
- **New positive tests**: valid PORT_STAFF membership, valid tenant ADMIN
  membership, platform ADMIN with explicit context, Organization in multiple
  ports (`test_vessel_link_multi_port_membership_allowed_in_each`), and correct
  reporting-unit historical audit
  (`test_audit_stores_reporting_unit_without_org_conflation`).
- Retained: composite cross-tenant rejections, DB cascade via direct SQL,
  ATB/ATD distinctness, blank/zero/invalid distinctness, fresh + pre-H2 migration
  preservation.

### Operational database blocker (unchanged this turn)

```text
Operational DB is stamped with rejected m12 and requires a separate,
Codex-reviewed reconciliation step after the corrected migration is accepted.
```

`data/cang_vu.db` still carries the earlier rejected m12 schema and was **not
touched, restored, downgraded, stamped or migrated** during this correction
(read-only check only: version `m12f0f000012`, no `reporting_units`,
`foreign_key_check` clean, 59 vessels, 0 declarations). No backup database was
modified. The reviewer's disposable copy `data/review_h2_corrected_migration.db`
is gitignored, was not staged, and is not operational evidence.

### Boundary / residual limitations

- No parser, import API, dashboard or UI (H3/H4). Not started.
- The DB retains ordinary user FKs for `created_by_user_id`/`reviewed_by_user_id`
  because platform ADMIN is an exception not encodable in one composite FK; the
  actor/reviewer authorization is therefore enforced fail-closed in the service
  layer and fully tested. H3 endpoints must call these validators.
- No raw workbook, render, database or backup committed; `templates/*.xlsx` and
  `data/` remain untracked/gitignored. No CVF-core change.

### Next governed move

- Codex review round 3 of the diff, corrected migration and tests. Do not commit,
  do not touch the operational DB, and do not start H3/H4 before this review
  passes.

---

## Historical TOS H2 correction round 3 — 2026-07-18

- **Status**: H2 CORRECTED AGAIN IN WORKING TREE — PENDING CODEX REVIEW ROUND 4.
  Not committed; not closed; H3/H4 not started.
- **Phase**: BUILD. REVIEW and FREEZE gates remain ahead.
- **Risk Level**: R2.
- **Order**: executed `docs/CLAUDE_H2_CORRECTION_ORDER_R3_20260718.md`
  (H2 REJECTED AFTER REVIEW ROUND 3). Two service-layer authorization defects
  only. The R2 schema, membership tables, composite foreign keys, tenant-scoped
  audit, migration and schema-drift verification are unchanged and not regressed.
  **No new migration** was needed; changes are limited to `backend/historical.py`
  and `tests/test_historical_import.py`.

### Exact authorization condition implemented

`backend/historical._authorize_unit_role` (shared by `validate_import_actor` and
`validate_reviewer`) now fails closed in this order:

1. an acting user must be supplied;
2. the reporting unit is loaded and must **exist and be active** (`is_active == 1`);
   this gate runs before any membership or platform-override decision, with
   distinct "does not exist" vs "is not active" messages, so no actor — not even
   a platform ADMIN with explicit context — may act on a missing or deactivated
   unit;
3. the user must be active and hold a permitted role (PORT_STAFF or ADMIN;
   CUSTOMER rejected);
4. membership in the **target** unit authorizes the permitted role;
5. otherwise a platform override is allowed only when `user.role == "ADMIN"`
   **and** `platform_context is True` **and** the user has **zero** rows in
   `reporting_unit_users` across the whole system. An ADMIN who belongs to any
   unit is tenant-local and can never use `platform_context=True` to reach a
   different unit; the caller-provided boolean alone is never sufficient.

- Defect 1 fixed: tenant ADMIN (member of Port A) + `platform_context=True` acting
  on / reviewing Port B is now rejected (added
  `user_has_any_unit_membership`).
- Defect 2 fixed: an inactive `ReportingUnit` is rejected for actor and reviewer,
  including for a genuine platform ADMIN with explicit context (added
  `_load_active_reporting_unit`).

### Five new negative tests (all pass)

- `test_tenant_admin_with_context_cannot_act_on_foreign_unit` — tenant ADMIN in
  Port A + context acting on import Port B → `HistoricalAuthorizationError`.
- `test_tenant_admin_with_context_cannot_review_foreign_unit` — same for reviewer.
- `test_import_actor_on_inactive_unit_rejected` — PORT_STAFF with valid membership
  on an inactive unit → rejected ("not active").
- `test_reviewer_on_inactive_unit_rejected` — reviewer on an inactive unit →
  rejected ("not active").
- `test_platform_admin_cannot_override_inactive_unit` — platform ADMIN (zero
  memberships) + explicit context on an inactive unit → rejected ("not active").

Retained positives: PORT_STAFF/tenant-ADMIN acting within a unit where they have
membership; a true platform ADMIN with zero memberships + explicit context acting
on an active unit; platform ADMIN without explicit context rejected.

### Evidence (disposable DBs only)

- `python -m pytest -q tests/test_historical_import.py`: 52 passed (47 prior + 5).
- `python -m pytest -q`: 148 passed (96 prior + 52).
- `python -m compileall backend` and the test module: PASS.
- `git diff --check`: PASS. One Alembic head: `m12f0f000012`.

### Operational database blocker (unchanged this turn)

```text
Operational DB is stamped with rejected m12 and requires a separate,
Codex-reviewed reconciliation step after the corrected migration is accepted.
```

`data/cang_vu.db` was **not touched** this turn (read-only check only: version
`m12f0f000012`, 59 vessels, 0 declarations). No backup database was modified. No
Alembic upgrade/downgrade was run against the operational database.

### Boundary

- No parser, import API, dashboard or UI (H3/H4). Not started.
- No raw workbook, render, database or backup committed; `templates/*.xlsx` and
  `data/` remain untracked/gitignored. No CVF-core change.

### Next governed move

- Codex review round 4 of the diff, migration and tests. Do not commit, do not
  touch the operational DB, and do not start H3/H4 before this review passes.

---

## Historical TOS H2 finalization — role model and DB reconciliation — 2026-07-18

- **Status**: H2 CLOSED / ACCEPTED for local/pilot scope. Codex review round 4
  accepted the implementation; this owner-authorized finalization applied the
  final role model and reconciled the operational database. Committed locally on
  one commit; not pushed. H3/H4 not started. Production readiness / FREEZE not
  claimed.
- **Phase**: BUILD → REVIEW complete for local scope.
- **Risk Level**: R2. Owner authorization: EXPLICIT.
- **Order**: `docs/CLAUDE_H2_FINALIZATION_PLATFORM_ADMIN_AND_DB_RECONCILIATION_20260718.md`.

### Superseding statement

The earlier handoff sections state the operational DB was stamped with the
rejected old m12 and needed a separate reconciliation. **That is now done.** The
operational database has been reconciled from the clean pre-m12 backup to the
accepted `m12f0f000012`. The earlier "rejected m12" statements are retained above
only as historical context.

### Final role model

`PLATFORM_ADMIN`, `PORT_STAFF`, `CUSTOMER` (no tenant-local ADMIN):

- `PLATFORM_ADMIN`: product-wide administration (reporting units, memberships,
  cross-tenant audit, migrations, backup/integration config, tenant identity);
  performs a tenant/historical operation only with an explicit platform context.
- `PORT_STAFF`: operates a reporting unit only with FK-backed membership; port
  declaration review/approval, port register, and (in H3/H4) historical import.
- `CUSTOMER`: customer-scoped; no internal TOS/historical authority.

Historical actor/reviewer authorization is now explicit: `PORT_STAFF` needs
membership in the active unit; `PLATFORM_ADMIN` needs `platform_context=True`
(membership neither required nor sufficient); a missing/inactive unit, CUSTOMER,
legacy `ADMIN` and inactive users are rejected. The prior "ADMIN with zero
memberships" inference was removed. The existing operational `admin` account was
converted to `PLATFORM_ADMIN` by a role-only data migration in `m12` (no password
hash read or changed; reversible on downgrade).

### RBAC surface updated

`backend/rbac.py` role enum; every `require_roles(...)` in `backend/app.py`
(system/maintenance endpoints → PLATFORM_ADMIN-only; operational endpoints keep
PLATFORM_ADMIN as allowed platform support); dashboard attention-queue map;
`backend/historical.py` validators; `frontend/app.js` role label
(`PLATFORM_ADMIN:'Platform admin'`) and visibility checks; `scripts/bootstrap_admin.py`
and `scripts/generate_appendix_operational_review.py`; and the test fixtures/mirrors.

### Controlled DB reconciliation evidence (no secrets / no personal data)

Files (absolute paths inside this repo's `data/`):

- Operational DB: `data/cang_vu.db`.
- Clean source backup (pre-m12): `data/backups/cang_vu-20260718-021834-pre-m12-historical.db`,
  SHA-256 `136389375c15d461e994094c9eb279b8e8f59e2ada78237c988f7038a96dce02`, alembic `l11f0f000011`.
- Immutable safety backup of the current DB before replacement:
  `data/backups/cang_vu-20260718-105213-pre-h2-final-reconcile.db`,
  SHA-256 `6087768510af18586d38a792f8e148d426687c5812f95e72822031e2b5b45414`
  (hash-matched the pre-replacement operational DB).

Inventory + logical live-data equality gate (read-only): both DBs
`integrity_check = ok`, `foreign_key_check` clean. All 14 non-H2 live tables
compared by column set, row count and deterministic ordered row hashes are
logically identical between the current operational DB and the clean backup; the
only operational-only tables were the six rejected old-m12 historical tables.
Before reconciliation: 59 vessels, 0 declarations, 8 audit events, `admin`
active legacy `ADMIN`.

Staging (disposable copies of the clean backup, Alembic pointed at staging only):
confirmed `l11f0f000011` before upgrade; applied corrected `m12`. Acceptance gate
passed — alembic current `m12f0f000012`, exactly one head, `integrity_check = ok`,
`foreign_keys = 1`, `foreign_key_check` clean; reporting_units + both membership
tables + composite tenant FKs + audit tenant FK present; all historical/membership/
reporting_units tables empty (no seed, no Tân Thuận row); 59 vessels retained;
every live table matches the clean source; `admin` now active `PLATFORM_ADMIN`
with zero legacy `ADMIN` and unchanged password hashes. A second disposable copy
passed upgrade → downgrade (restored `l11`, legacy `ADMIN`, 59 vessels, no H2
tables) → re-upgrade.

Replacement: pre-replacement operational SHA-256 re-confirmed equal to the safety
backup; `data/cang_vu.db` replaced by an exact-file copy of the accepted staging;
post-replacement operational SHA-256 `555928567b833eb300c598af6d370918761de50d9c5a09d88dc57d5d8f2a609b`.
Post-replacement read-only validation passed: alembic `m12f0f000012`, integrity
`ok`, FK check clean, 59 vessels, 0 declarations, 8 audit events, all H2/membership/
reporting_units tables present and empty, `admin` active `PLATFORM_ADMIN`, no legacy
`ADMIN`.

Before → after operational counts: vessels 59 → 59; declarations 0 → 0;
audit_events 8 → 8. Alembic before/after (schema identity): rejected old `m12`
(organization-based) → accepted `m12f0f000012` (ReportingUnit/membership-based).

### Evidence (tests)

- `python -m pytest -q tests/test_historical_import.py`: 53 passed.
- `python -m pytest -q`: 149 passed. `git diff --check`: PASS. One Alembic head.

### Boundary

- No parser, import API, dashboard or UI (H3/H4). Not started. No TOS/workbook
  data imported.
- Only `data/cang_vu.db` was replaced. No backup, workbook, staging/review DB,
  render, CVF-core or out-of-repo file was modified. Databases and workbooks
  remain untracked/gitignored. Nothing pushed.

---

## Historical TOS H2 correction R4 — live tenant context — 2026-07-18

- **Status**: CLOSED / ACCEPTED for local/pilot scope after independent Codex
  completion and verification. This section supersedes the earlier statement
  that live operational endpoints merely allowed PLATFORM_ADMIN by role.
- **Phase**: BUILD → REVIEW complete. Production readiness / FREEZE not claimed.
- **Risk**: R2; database reconciliation was explicitly authorized by the owner.
- **Order**: `docs/CLAUDE_H2_CORRECTION_ORDER_R4_TENANT_CONTEXT_20260718.md`.

### Implemented boundary

- `backend/tenant.py` is the shared fail-closed live-operation guard.
  `PORT_STAFF` needs an FK-backed membership in the explicit active unit;
  `PLATFORM_ADMIN` must provide explicit `X-Reporting-Unit-ID`; CUSTOMER remains
  Organization-scoped. Missing, malformed, unknown and inactive contexts fail.
- Live vessel, crew, declaration, workflow, import/export, dashboard, reports,
  report adjustments and prepared integration payloads are scoped server-side.
  Platform backup/tenant-management operations remain platform-wide.
- Forward migration `n13f0f000013` adds `reporting_unit_vessels` and tenant
  provenance to report adjustments, import jobs and sync jobs. The legacy
  `vessels.is_port_tracked` field is compatibility-only, not a tenant boundary.
- `frontend/app.js` sends the selected unit on tenant calls. PORT_STAFF may use
  only membership units; PLATFORM_ADMIN deliberately selects one. The UI has no
  implicit all-ports tenant view and reloads/clears stale state on context change.
- `scripts/bootstrap_reporting_unit.py` is argument-driven, idempotent and
  dry-run by default. It aborts on ambiguous identity/membership and never
  hard-codes usernames or a commercial port into the reusable migration.

### Staging and operational reconciliation evidence

Staging was made through SQLite backup API from the m12 operational database.
Upgrade to n13 plus dry-run/apply bootstrap passed: `integrity_check=ok`, runtime
`foreign_keys=1`, `foreign_key_check` empty, 59 vessels retained, one unit, one
PORT_STAFF membership, two Organization links, 59 register links and four scoped
existing import jobs. The disposable staging DB and manifest were removed after
evidence capture.

Fresh pre-R4 operational backup (gitignored):

- `data/backups/cang_vu-20260718-123933-pre-r4-tenant-context.db`
- SHA-256 `f01e0e2aa4ea865fc09b1ca1ac670b836f5987510bfe35d745bb11dc3ff46d33`
- revision `m12f0f000012`; 59 vessels; 0 declarations; 8 audit events;
  integrity `ok`; FK check clean.

Operational database after accepted staging gates and bootstrap:

- SHA-256 `f2baa3f283706d0680a797b5b192ffdfb83cf62c15d11004d9fb11d13342c822`
- revision `n13f0f000013`; runtime `foreign_keys=1`; integrity `ok`; FK check clean;
- 59 vessels, 0 declarations and 9 audit events (one explicit bootstrap audit);
- Cảng Tân Thuận unit `TAN-THUAN`: one `nhanviencang` PORT_STAFF membership,
  two Organization links and 59 register links;
- all four existing import jobs mapped to the unit;
- `admin` remains active PLATFORM_ADMIN; password hashes were not read or changed.

Before → after business counts: vessels 59 → 59; declarations 0 → 0. The only
new audit row records the controlled legacy-unit bootstrap.

### Verification

- `python -m pytest -q`: **158 passed**, one retained openpyxl warning.
- Two-unit HTTP tests prove membership rejection, explicit platform context,
  inactive/malformed context rejection, list/export/dashboard isolation,
  cross-unit mutation/workflow denial, independent port registers, correct
  tenant audit and CUSTOMER denial from internal port operations.
- Bootstrap dry-run/apply/idempotency has an automated regression test.
- Python compile checks and `git diff --check`: pass; Alembic has one head.

### Boundary and next move

- No raw TOS workbook was modified, imported or committed. Databases/backups are
  gitignored. The four raw `templates/*.xlsx` files remain intentionally
  untracked.
- H3 parser/import API and H4 historical dashboard UI remain not started.

---

## Historical TOS H3A — parser and import API — 2026-07-18

- **Status**: IMPLEMENTED / VERIFIED for audited TOS Berth, TOS container-detail
  and legacy 35-column PL.03. H3 remains open only for owner-deferred PL.01/PL.02
  samples and their monthly/YTD semantics.
- **Phase**: BUILD; R2. No production-readiness/FREEZE claim.

### Implemented

- `backend/historical_tos_parser.py`: memory-bounded, filename-independent
  structural detection; strict ATB/ATD, call key, TEU, F/E, trade, movement and
  tonne transforms; safe errors; raw/cell provenance. Hidden data is included.
- `backend/historical_api.py`: tenant-scoped preview, paginated rows/history,
  confirm, idempotency, explicit revision conflict decision and audited vessel
  link resolution. Source copies are checksum-addressed outside Git.
- Migration `o14f0f000014` permits Detail-to-Berth links across immutable source
  imports while preserving the composite reporting-unit FK. Active cargo links
  follow a confirmed corrected Berth revision instead of a superseded call.
- Legacy PL.03 is preserved as reported facts; its ETA-derived AG/AH values do
  not override TOS ATB/ATD. No declaration/master/live record is synthesized.

### Workbook evidence reused, not re-audited

The committed Desktop Codex audit/mapping remained the contract. A minimal
read-only parser verification reproduced 40 Berth rows, 1,067 Detail rows, 38
matched cargo-call keys, two calls without Detail and 73 PL.03 rows. Aggregates
match the audit exactly: load E 79/149 TEU/351.40 t; load F 225/443/2,984.37 t;
unload E 682/1,189/2,415.78 t; unload F 81/142/2,143.28 t.

### Database and regression evidence

- Pre-H3 backup: `data/backups/cang_vu-20260718-131730-pre-h3.db`, SHA-256
  `f01b5c1eebf3ddd282cd8510963e74afa1c265372ad65f247bef9d656efad1ea`.
- Staging upgrade, downgrade to n13 and re-upgrade passed: integrity `ok`, zero
  FK errors, one head `o14f0f000014`, 59 vessels and 9 audit events retained.
- The downgrade fails closed once real cross-import TOS links exist because n13
  cannot represent them; it never silently nulls or rewrites imported evidence.
- Operational DB upgraded only after staging passed. Post-upgrade SHA-256
  `e34390aa9c99dccd948974b7732ddf709a171031496dabbf1bf43e2ebe2b1ddf`;
  integrity `ok`, zero FK errors, 59 vessels, 0 declarations, 9 audit events,
  one unit, one staff membership, two Organization links and 59 register links.
- `python -m pytest -q`: **163 passed**, one retained openpyxl warning.

### Boundary / next move

- No source workbook was changed or committed; no workbook/database/backup is
  in Git and nothing was pushed.
- H4 can now implement the separate historical import workspace and review
  queues. PL.01/PL.02 parser completion remains deferred until representative
  source files are supplied, as approved by the owner.

---

## Historical TOS H4A — import workspace UI — 2026-07-18

- **Status**: IMPLEMENTED / VERIFIED locally. H4 remains open for historical,
  live and combined dashboard/report-source selection (H4B).
- **Phase/Risk**: BUILD / R2. No deployment or production-readiness claim.

### Delivered

- Import now has separate `Dữ liệu vận hành` and `Lịch sử / TOS` tab panels.
  The historical boundary explicitly says it does not alter declarations,
  vessel master, crew or current operational data.
- H3A APIs are exposed as a four-step workflow: structural detection, preview,
  explicit overlap decision and confirmation. Source kind, ATB month, mapping,
  checksum, counts and paginated row evidence are visible before activation.
- Import history shows revision/supersession state and lets staff reopen a
  pending preview. Cancel is a server-side audited transition, not a client-only
  dismissal. Conflict actions say “keep active” versus “activate new revision”
  and require a reason for the latter.
- TOS vessel-link review displays the raw TOS name, suggested/selected register
  vessel and explicit accept/reject actions. Backend detail, queue and cancel
  endpoints remain tenant-scoped and reject cancelled/superseded mutations.
- Layout is responsive and keyboard-accessible without replacing the existing
  static HTML/CSS/JS architecture or adding browser storage as business truth.

### Verification and boundary

- `python -m pytest -q`: **164 passed**, one retained openpyxl warning.
- Static HTML parser: 138 ids, zero duplicates. Python compile and diff checks
  pass. Browser visual QA was not requested and was not claimed.
- No workbook/database/backup is included in Git; no deployment and no push.
- Next move: H4B source-aware historical/live/combined dashboard and overlap
  coverage indicators. PL.01/PL.02 remain owner-deferred pending real samples.

---

## Historical TOS H4B — source-aware reporting dashboard — 2026-07-18

- **Status**: IMPLEMENTED / VERIFIED locally. H4 owner UAT remains open.
- **Phase/Risk**: BUILD / R2. No deployment or production-readiness claim.

### Delivered

- Extended the existing analytics API and UI with explicit `LIVE`, `LỊCH SỬ`
  and `KẾT HỢP` modes. Live-approved remains the default and the only mode
  available to CUSTOMER; internal modes require a tenant-resolved port scope.
- Historical call counts use active validated Berth rows by TOS ATB. Tonnes and
  TEU use active, validated, matched Detail rows. PL.03 ETA-era times are not
  used to reconstruct the trend.
- API and UI expose monthly coverage, source badges, warning text and
  completeness. Review-pending or absent facts return `null` and render as a
  dash rather than a misleading zero.
- Combined totals fail closed when a month has both live-approved declarations
  and active historical coverage. The UI hides totals and export; the server
  independently rejects combined XLSX with `409`.

### Verification and boundary

- `python -m pytest -q`: **166 passed**, one retained openpyxl warning. Targeted
  regression covers historical aggregation, empty-container weight,
  source authorization, partial coverage, combined no-overlap, overlap blocking
  and export rejection.
- Python compilation and `git diff --check` pass. Browser visual QA, deployment
  and owner UAT are not claimed.
- Raw workbooks remain untracked and untouched; no database/backup is committed
  and nothing is pushed.
