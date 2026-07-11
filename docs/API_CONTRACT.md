# API Contract — Khai-bao-Cang-vu

> Generated: 2026-07-11
> Tranche: T1 Identity, RBAC & Tenant Isolation (WO-KBCV-T1-20260711)
> Backend: FastAPI + SQLAlchemy (SQLite local / PostgreSQL production)
> Auth: JWT Bearer (`Authorization: Bearer <token>`)

## Role-Based Access Control & Tenant Scope

This system implements four roles with distinct scopes of operations.

*   **ADMIN**: Global administrator. Has access to all organizations, vessels, crew, and declarations. Restricted from workflow approval actions (`CV_APPROVE`, `QLC_APPROVE`, `BP_APPROVE`, `ISSUE`, `REVOKE`, `REQUEST_CHANGES`).
*   **CUSTOMER**: Customer representative. Has tenant-isolated access. Can only view/write resources belonging to their `organization_id`.
*   **CV**: Port Officer (Cảng vụ viên). Global read access to submitted/approved declarations. Allowed to perform `CV_APPROVE` and `REQUEST_CHANGES` on declarations.
*   **QLC**: Port Manager (Quản lý cảng). Global read access. Allowed to perform `QLC_APPROVE` and `REQUEST_CHANGES` on declarations.
*   **BP**: Permission Officer (Ban cấp phép). Global read access. Allowed to perform `BP_APPROVE`, `ISSUE`, `REVOKE`, and `REQUEST_CHANGES` on declarations.

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
| POST | `/api/declarations/{id}/workflow` | CV, QLC, BP | `WorkflowActionRequest` | `Declaration` |

*   **Tenant Constraint**: If `CUSTOMER`, GET/POST/attachments are strictly restricted to own organization's declarations.
*   **Paging Contract**: Existing callers without `page` receive the compatible
    array response. Callers sending `page` receive `{items, page, page_size,
    total, total_pages, sort, direction}`. Sort is allowlisted to
    `updated_at`, `declaration_date`, `reference_no` and `workflow_status`;
    `direction` is `asc` or `desc`.
*   **Workflow Constraints**:
    *   Only `CUSTOMER` is allowed to submit a declaration (`submit=true`).
    *   `ADMIN` is denied from workflow actions.
    *   `CV`, `QLC`, `BP` are restricted to their specific actions (see below).
    *   Actor name and role are derived strictly from the authenticated JWT session, ignoring client-supplied payloads to guarantee audit trail integrity.

#### Workflow State Machine
```
DRAFT → PENDING_REVIEW  (on submit=true)
PENDING_REVIEW → PENDING_QLC  (CV_APPROVE)
PENDING_QLC → PENDING_BP  (QLC_APPROVE)
PENDING_BP → APPROVED  (BP_APPROVE)
APPROVED → ISSUED  (ISSUE, requires permit_no)
any → CHANGES_REQUESTED  (REQUEST_CHANGES, requires note)
any → REVOKED  (REVOKE, requires note)
```

### SUGGESTIONS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/suggestions?field=`| Any | `field` ∈ {last_port, working_port, destination_port, master_name} | `[string]` |

*   **Tenant Constraint**: Suggestions are computed over the user's tenant scope if `CUSTOMER`.

### DATA IMPORT

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| POST | `/api/import/vessels` | CUSTOMER, ADMIN | XLSX body | `{accepted, rejected}` |
| POST | `/api/import/declaration`| CUSTOMER, ADMIN | XLSX body | `{accepted, rejected, id}` |

*   **Tenant Constraint**: Imported vessels/declarations are automatically bound to the logged-in customer's `organization_id`.

### REPORTS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/reports/appendix1` | CUSTOMER, CV, QLC, BP, ADMIN | date range | XLSX download |
| GET | `/api/reports/appendix2` | CUSTOMER, CV, QLC, BP, ADMIN | date range | XLSX download |
| GET | `/api/reports/appendix3` | CUSTOMER, CV, QLC, BP, ADMIN | date range | XLSX download |

*   **Tenant Constraint**: CUSTOMER receives only records from its own organization; reviewers and ADMIN receive the operational scope allowed by their role.

### INTEGRATIONS

| Method | Path | Allowed Roles | Request | Response |
|--------|------|---------------|---------|----------|
| GET | `/api/integrations/maritime-authority` | BP, ADMIN | — | `{connector, jobs}` |
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
