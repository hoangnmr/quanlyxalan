# H2 correction order R4 — enforce tenant context on live operations

Date: 2026-07-18
Reviewer: Codex
Phase: BUILD
Risk: R2
Status: REQUIRED — H2 is not accepted

## 1. Blocking defect

The database reconciliation and legacy `ADMIN -> PLATFORM_ADMIN` conversion
passed, but the final role contract is not enforced by the existing live APIs.

Reproduction against the reconciled operational database:

```text
nhanviencang | PORT_STAFF     | 0 reporting-unit memberships | sees 59 vessels | sees 59 register rows
admin        | PLATFORM_ADMIN | 0 reporting-unit memberships | sees 59 vessels | sees 59 register rows
```

Examples are `/api/vessels` and `/api/port-vessel-register`. They authorize by
role name only and query globally. `PLATFORM_ADMIN` is not required to provide
an explicit ReportingUnit context. Similar live endpoints must be audited; do
not fix only these two examples.

This violates the approved contract:

- `PORT_STAFF` operates only ReportingUnits backed by
  `reporting_unit_users` membership;
- `PLATFORM_ADMIN` may operate tenant data only with an explicit active
  ReportingUnit context;
- tenant data from multiple ReportingUnits is never combined implicitly;
- `CUSTOMER` remains restricted to its own Organization.

## 2. Required implementation

### 2.1 Introduce one reusable live-operation context guard

Implement a single backend dependency/service for tenant-bound requests. Do
not duplicate ad-hoc checks in individual routes.

For a tenant-bound operation it must:

1. require an explicit ReportingUnit identifier in the request context (a
   documented header such as `X-Reporting-Unit-ID` is acceptable);
2. verify the ReportingUnit exists and is active;
3. for `PORT_STAFF`, require an FK-backed row in `reporting_unit_users`;
4. for `PLATFORM_ADMIN`, require the explicit context but not membership;
5. reject `CUSTOMER` from port-internal operations and retain existing
   Organization ownership rules on customer operations;
6. expose the resolved ReportingUnit id to queries, mutations and audit events;
7. return deterministic `400/403/404` responses without leaking another
   tenant's data.

System-wide platform operations such as backup management, ReportingUnit
management and membership management remain platform-scoped and must not be
mistaken for tenant operations.

### 2.2 Audit and scope every live endpoint

Inspect every `require_roles(...)` use in `backend/app.py` and classify it as:

- platform-wide system operation;
- customer Organization operation; or
- ReportingUnit-bound port operation.

For every ReportingUnit-bound read, export, create, update, delete, approval,
import and report endpoint:

- apply the shared context guard;
- scope reads through `reporting_unit_organizations` and the resolved unit;
- verify the target Organization belongs to that unit before mutations;
- verify referenced Vessel, Declaration, Crew and Import records are inside the
  resolved unit before use;
- write `reporting_unit_id` into audit events when the action is tenant-bound;
- never fetch globally and filter only in the frontend.

At minimum cover vessels, port vessel register, declarations, crews, operational
Excel import/export, approval/review flows, reports and dashboard aggregates.
The audit is incomplete if any `PORT_STAFF` route remains role-only.

### 2.3 Make the port vessel register tenant-safe

The global `vessels.is_port_tracked` flag cannot represent different register
membership for different ports. Add a normalized FK-backed association (for
example `reporting_unit_vessels`) or an equivalently safe design.

Requirements:

- the same Vessel may be tracked by unit A and not tracked by unit B;
- list/add/remove/export use the resolved ReportingUnit association;
- do not use the legacy global boolean as the authorization or tenant boundary;
- preserve compatibility only where necessary and document its deprecation;
- use a forward Alembic migration after applied `m12f0f000012`; do not silently
  rewrite an already-applied migration.

### 2.4 Bootstrap the existing single-port installation safely

The operational database currently has 59 vessels but zero ReportingUnits and
zero memberships. Do not leave `PORT_STAFF` locked out and do not bypass the
new guard.

Provide an idempotent, argument-driven bootstrap/reconciliation command that:

- creates the initial active ReportingUnit for the current port;
- links the intended existing Organizations to it;
- assigns the intended existing port-staff user through
  `reporting_unit_users`;
- maps the existing 59 tracked vessels to that unit's register association;
- does not hard-code usernames, ids or a commercial port name in a reusable
  schema migration;
- supports preview/dry-run and produces counts without exposing secrets;
- aborts on ambiguity instead of guessing.

Run it on staging first. Before changing the operational database, create a new
timestamped backup and record SHA-256 hashes. Replace/apply operational state
only after all staging gates pass.

### 2.5 Add the minimum UI context

The frontend must send the selected ReportingUnit context on tenant-bound API
calls.

- `PORT_STAFF` may select only active units from its memberships;
- `PLATFORM_ADMIN` must deliberately select an active unit before opening or
  mutating tenant data;
- show the active port/reporting unit clearly in the UI;
- changing context must reload scoped data and clear stale selections;
- never silently fall back to a global/all-ports tenant view;
- `CUSTOMER` UX remains Organization-scoped.

Do not build the future historical-import UI in this correction.

### 2.6 Synchronize documentation

Update the Historical roadmap and handoff so that all active decisions use only
`PLATFORM_ADMIN`, `PORT_STAFF` and `CUSTOMER`. Remove stale operational phrases
such as `PORT_STAFF/ADMIN` and `ADMIN/PORT_STAFF`.

Do not claim H2 closed until Codex review accepts this correction.

## 3. Mandatory regression tests

Create at least two active ReportingUnits, two Organizations and separate staff
memberships. Test through HTTP/API boundaries, not only helper functions.

Required proofs:

1. `PORT_STAFF` with no membership is rejected.
2. Staff of unit A cannot read, export, mutate, approve or delete unit B data.
3. Unit A list/report/dashboard totals never include unit B data.
4. `PLATFORM_ADMIN` without an explicit unit context is rejected for tenant
   operations.
5. `PLATFORM_ADMIN` with context A sees/mutates only A; context B sees/mutates
   only B.
6. Missing, malformed and inactive unit contexts are rejected.
7. An Organization not linked to the selected unit cannot be used in a create
   or update request.
8. Port-register membership is independent between units A and B.
9. Tenant-bound audit events contain the correct `reporting_unit_id`.
10. `CUSTOMER` cannot access internal port/TOS operations and cannot cross its
    Organization boundary.
11. The migrated operational fixture still contains exactly 59 vessels and its
    initial unit register contains exactly the intended 59 vessels.
12. All pre-existing tests plus the new tests pass.

Do not weaken assertions or rewrite tests merely to accommodate global access.

## 4. Database and Git safety gates

- Work from a copy for migration/reconciliation testing.
- Create a fresh pre-R4 operational backup.
- Verify Alembic head/current, `PRAGMA integrity_check`,
  `PRAGMA foreign_key_check` and `PRAGMA foreign_keys = 1`.
- Compare the 59 vessels and existing audit events before/after.
- Record staging and operational database SHA-256 hashes in the report/handoff.
- Do not commit any `.db`, backup, workbook or extracted customer data.
- Preserve the four raw untracked workbooks under `templates/`; do not modify,
  delete or stage them.
- Commit the correction separately; do not amend away the audit trail unless
  explicitly ordered.

## 5. Delivery report format

Return only a concise implementation report containing:

1. commit hash;
2. files and migrations changed;
3. endpoint classification summary and shared context mechanism;
4. bootstrap/reconciliation command and resulting non-sensitive counts;
5. staging/operational integrity, FK and SHA-256 evidence;
6. tests run and exact result;
7. proof for the twelve regression cases above;
8. `git status --short`, confirming only the known raw workbooks remain
   untracked;
9. known limitations, if any.

H2 remains **IN_PROGRESS / NOT ACCEPTED** until independent Codex review.
