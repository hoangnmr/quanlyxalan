# API Contract — Khai-bao-Cang-vu

> Generated: 2026-07-11
> Tranche: T1 Identity, RBAC & Tenant Isolation (WO-KBCV-T1-20260711)
> Backend: FastAPI + SQLAlchemy (SQLite local / PostgreSQL production)
> Auth: JWT Bearer (`Authorization: Bearer <token>`)

## Role-Based Access Control & Tenant Scope

This system implements three roles with distinct scopes of operations.

*   **ADMIN**: Global administrator. Has access to organizations, vessels, crew, declarations, reports, and integration preparation. Restricted from port review decisions.
*   **CUSTOMER**: Customer representative. Has tenant-isolated access. Can only view/write resources belonging to their `organization_id`.
*   **PORT_STAFF**: Nhân viên doanh nghiệp cảng. Can review customer declarations and perform `PORT_APPROVE` or `REQUEST_CHANGES`.

---

## Endpoints

### AUTH & PROFILE

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| POST | `/api/auth/login` | None | `{username, password}` | `{access_token, token_type}` |
| GET | `/api/auth/me` | Bearer (Any) | — | `{id, username, full_name, role, organization_id, is_active}` |
| POST | `/api/auth/logout` | Bearer (Any) | — | `{"detail": "Logged out"}` |

> **Rate Limiting**: Throttling is applied per IP. Over 5 incorrect login attempts within 5 minutes will temporarily lock the source IP.

### HEALTH & CATALOGS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/health` | None | — | `{status, database, version}` |
| GET | `/api/catalogs` | None | — | `{vesselTypes, vesselClasses, shellMaterials, cargoTypes, unloadMovements, loadMovements}` |

### ORGANIZATIONS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/organizations` | ADMIN | — | `[Organization]` |

### DASHBOARD

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/dashboard?q=` | Any | query `q` (optional) | `{stats, recent, matches}` |

*   **Tenant Constraint**: If `CUSTOMER`, stats and matches are strictly filtered to the user's `organization_id`. Others see global stats.
*   **Attention Queue**: `attention` is a role-scoped dashboard hint, containing
    only visible statuses and up to five oldest items. It does not grant an
    action; workflow authorization remains enforced by the API.
*   **Demo Marker**: `demo_mode=true` only when the local sentinel-marked demo
    dataset is present. The UI must show that it is not operational data.

### VESSELS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/vessels` | Any | — | `[Vessel]` |
| POST | `/api/vessels` | CUSTOMER, ADMIN | `VesselSaveRequest` | `Vessel` |
| POST | `/api/vessels/{id}/verify-registry` | CUSTOMER, ADMIN | — | `Vessel` |

*   **Tenant Constraint**: If `CUSTOMER`, GET only returns vessels belonging to the user's `organization_id`. POST validates that the vessel belongs to the user's `organization_id` or creates it bound to their organization. Registry verification is constrained to own organization's vessels.
*   **Verification Note**: Verification checks internal registry certificates locally and logs `source=local`.

### CREW

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/crew` | Any | — | `[CrewMember]` |
| POST | `/api/crew` | CUSTOMER, ADMIN | `CrewSaveRequest` | `CrewMember` |

*   **Tenant Constraint**: If `CUSTOMER`, resources are strictly filtered to the user's `organization_id`. Write operations verify the target vessel and crew belong to the user's organization.

### NOTIFICATION PREFERENCES

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/notification-preferences` | Authenticated | — | `{in_app_certificate_reminders}` |
| PUT | `/api/notification-preferences` | Authenticated | `{in_app_certificate_reminders: boolean}` | same |

The only active delivery is in-app certificate reminder visibility. Changes are
recorded in the audit trail. Email and Teams are intentionally not represented
as active choices until their connectors and delivery controls are approved.

### DECLARATIONS & WORKFLOW

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/declarations` | Any | query filters; optional `page`, `page_size` (1–100), `sort`, `direction` | `[Declaration]` or paged envelope |
| POST | `/api/declarations?submit=false` | CUSTOMER, ADMIN | `DeclarationSaveRequest` | `Declaration` |
| POST | `/api/declarations?submit=true` | CUSTOMER | `DeclarationSaveRequest` | `Declaration` |
| POST | `/api/declarations/{id}/attachments` | CUSTOMER, ADMIN | raw file body | `Attachment` |
| GET | `/api/declarations/{id}/events` | Any | — | `[DeclarationEvent]` |
| POST | `/api/declarations/{id}/workflow` | PORT_STAFF | `WorkflowActionRequest` | `Declaration` |

*   **Tenant Constraint**: If `CUSTOMER`, GET/POST/attachments are strictly restricted to own organization's declarations.
*   **Paging Contract**: Existing callers without `page` receive the compatible
    array response. Callers sending `page` receive `{items, page, page_size,
    total, total_pages, sort, direction}`. Sort is allowlisted to
    `updated_at`, `declaration_date`, `reference_no` and `workflow_status`;
    `direction` is `asc` or `desc`.
*   **Workflow Constraints**:
    *   Only `CUSTOMER` is allowed to submit a declaration (`submit=true`).
    *   `ADMIN` is denied from workflow actions.
    *   `PORT_STAFF` can confirm approval or request changes.
    *   Actor name and role are derived strictly from the authenticated JWT session, ignoring client-supplied payloads to guarantee audit trail integrity.

#### Workflow State Machine
```
DRAFT → PENDING_REVIEW  (customer confirms and sends)
PENDING_REVIEW → APPROVED  (PORT_APPROVE)
PENDING_REVIEW → CHANGES_REQUESTED  (REQUEST_CHANGES, requires note)
CHANGES_REQUESTED → PENDING_REVIEW  (customer confirms and sends again)
```

Legacy actions `CV_APPROVE`, `QLC_APPROVE`, `BP_APPROVE`, `ISSUE`, and
`REVOKE` are retired and return HTTP `410 Gone`; they cannot move a record into
an obsolete status.

### SUGGESTIONS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/suggestions?field=`| Any | `field` ∈ {last_port, working_port, destination_port, master_name} | `[string]` |

*   **Tenant Constraint**: Suggestions are computed over the user's tenant scope if `CUSTOMER`.

### DATA IMPORT

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| POST | `/api/import/vessels?preview=true` | CUSTOMER, ADMIN | XLSX body | `{preview, mapping, rows, checksum}` |
| POST | `/api/import/vessels` | CUSTOMER, ADMIN | XLSX body | `{accepted, rejected, mappingVersion, checksum}` |
| POST | `/api/import/declaration?preview=true` | CUSTOMER | XLSX body | `{preview, row, checksum}` |
| POST | `/api/import/declaration`| CUSTOMER | XLSX body | `{accepted, rejected, id, mappingVersion, checksum}` |

*   **Tenant Constraint**: Imported vessels/declarations are automatically bound to the logged-in customer's `organization_id`.
*   **Mapping `KBCV-IMPORT-1.2`**: vessel workbooks are detected by normalized Vietnamese header labels across sheet names and header rows. Required fields are Tên phương tiện, Số đăng ký, Loại phương tiện and Cấp phương tiện. Scalar numeric fields containing multiple certified values (for example `2723.79 / 2912.57`) use the first listed value and preserve the complete source cell in `notes`; preview returns `mappingWarnings`. Declaration workbooks are detected by field labels with the published template cells retained as fallback.
*   **External link safety**: passive Excel `hyperlink` and `externalLinkPath` relationships are ignored and never fetched. Other external relationship types remain rejected.
*   **Demo transition**: the sentinel demo dataset is removed on first real create/import. A demo CUSTOMER keeps its organization/user binding while the sentinel is cleared and the real organization profile is applied.

### HISTORICAL TOS / PL.03 IMPORT (H3A)

All routes require an explicit `X-Reporting-Unit-ID`. `PORT_STAFF` must have an
FK-backed membership in that unit; `PLATFORM_ADMIN` must deliberately select the
unit. `CUSTOMER` is denied.

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/historical-imports/preview` | XLSX body; optional `X-Source-Filename` provenance | detected source, checksum, mapping receipt, counts, conflicts |
| GET | `/api/historical-imports` | `page`, `page_size` | tenant-scoped import history |
| GET | `/api/historical-imports/{id}` | — | import detail, conflicts and mapping receipt |
| GET | `/api/historical-imports/{id}/rows` | `page`, `page_size`, optional `status=VALID|REVIEW|REJECTED` | cell-provenance preview rows with warning codes |
| GET | `/api/historical-imports/{id}/vessel-links` | optional status, pagination | vessel-link review queue |
| POST | `/api/historical-imports/{id}/confirm` | optional conflict action/reason | committed, review, rejected or superseded revision state |
| POST | `/api/historical-imports/{id}/cancel` | reason | cancel a PREVIEWED import without activating facts |
| POST | `/api/historical-imports/{id}/vessel-links/{link_id}/resolve` | accept/reject candidate | audited link decision |

The browser may select several historical workbooks in one upload action. Each
workbook still creates or reuses its own checksum-backed import receipt; this is
not a merged opaque upload. After a Berth import is confirmed, the server
reconciles both active and still-PREVIEWED cargo-detail imports in the same
reporting unit, updates their row match/validation states and refreshes their
counts. The UI can then reopen the cargo receipt without uploading it again.

Detection is based on approved sheet/header/structure signatures, not the file
name. A repeated checksum is idempotent. Overlap never overwrites silently:
confirmation must choose `KEEP_EXISTING` or `ACTIVATE_NEW_REVISION` and a new
revision requires a reason. TOS ATB/ATD remains distinct and authoritative;
legacy PL.03 time is stored only as reported provenance.

Numeric extraction accepts Excel numeric cells and audited text representations
using Vietnamese or English separators: `331,47`, `331.47`, `1.088,84` and
`1,088.84`. Decimal-comma support is versioned as `tos_cargo_detail_v2` and
`reported_pl03_35col_historical_v2` (`KBCV-HIST-TOS-1.1`), so uploading a file
previously previewed under v1 creates a corrected receipt instead of reusing the
stale validation result.

Warning codes remain in provenance as audit evidence, but the UI does not show
them as active errors after a row becomes `VALID`. A confirmed Berth receipt
reconciles matching Detail receipts, including receipts already in `REVIEW`;
resolved Detail rows/counts update in place. When the same source checksum is
reprocessed under a newer mapping, an active older mapping is an explicit
revision conflict even if the legacy workbook has no trustworthy report period.
Activating the corrected receipt marks the older one `SUPERSEDED`.

### REPORTING UNIT ADMINISTRATION

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/reporting-units` | PORT_STAFF, PLATFORM_ADMIN | — | Active units visible to the caller |
| POST | `/api/reporting-units` | PLATFORM_ADMIN | `{name, code}` | Creates an empty active unit and records a tenant-scoped audit event |

Creating a unit never copies memberships, customer organizations, vessels,
declarations or historical facts from the currently selected unit. The new
unit must be configured separately before PORT_STAFF can operate it.

### REPORTS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/reports/appendix1` | CUSTOMER, PORT_STAFF, ADMIN | date range | XLSX download |
| GET | `/api/reports/appendix2` | CUSTOMER, PORT_STAFF, ADMIN | date range | XLSX download |
| GET | `/api/reports/appendix3` | CUSTOMER, PORT_STAFF, ADMIN | date range | XLSX download |
| GET | `/api/reports/analytics` | CUSTOMER (`source=live` only), PORT_STAFF, PLATFORM_ADMIN with explicit unit context | `period=week\|month\|quarter\|year`, `source=live\|historical\|combined` (default `live`), optional `as_of` | `{period, source, dataSource, combinedAllowed, kpis, trend, coverage, meta}`; combined KPI values are `null` while source overlap is unresolved |
| GET | `/api/reports/analytics/export` | Same as analytics | Same query as analytics | XLSX download; returns `409` instead of exporting an unresolved combined total |

*   **Tenant Constraint**: CUSTOMER receives only records from its own organization; reviewers and ADMIN receive the operational scope allowed by their role.
*   Analytics includes only declarations in `APPROVED` and compares the selected period with the same period of the previous year. `dataSource=DEMO` is a display marker only; it is not governance evidence.

### INTEGRATIONS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/integrations/maritime-authority` | ADMIN | — | `{connector, jobs}` |
| POST | `/api/integrations/prepare-sync` | ADMIN | `{from, to}` | `{id, recordCount, status}` |

---

## Attachment rules

| Property | Limit |
|----------|-------|
| Max size | 12 MB |
| Allowed extensions | .jpg, .jpeg, .png, .webp, .pdf, .doc, .docx, .xls, .xlsx |
| Magic byte check | Yes — extension must match file header |

## Error shape

All errors return JSON: `{"detail": "<message>"}` (FastAPI standard).
*   **401 Unauthorized**: User is unauthenticated (missing or invalid token).
*   **403 Forbidden**: User is authenticated but lacks required role or tries to access another tenant's resource.
*   **429 Too Many Requests**: Request blocked by rate-limiting.
