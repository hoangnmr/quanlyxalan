# Claude correction order R2 — H2 tenant membership and audit closure

Date: 2026-07-18  
Reviewer: Codex  
Phase: BUILD  
Risk: R2  
Status: H2 REJECTED AFTER REVIEW ROUND 2; H3/H4 BLOCKED

## 1. Task

Correct only the remaining H2 blockers described here. The previous correction
successfully introduced `ReportingUnit`, composite historical foreign keys and
SQLite FK enforcement; preserve those passing parts.

Read:

- `AGENTS.md`
- `.cvf/manifest.json`
- `.cvf/policy.json`
- `../WORKSPACE_RULES.md`
- `docs/CLAUDE_H2_CORRECTION_ORDER_20260718.md`
- `docs/AGENT_HANDOFF.md`
- `docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md`

Do not ask the user to paste the review. This file is the authoritative R2
order.

## 2. Verified passing baseline

Codex independently verified:

- distinct `ReportingUnit` architecture;
- historical child/import composite tenant constraints;
- cross-unit revision rejection;
- SQLite `PRAGMA foreign_keys = 1`;
- database-level cascade;
- migration upgrade/downgrade/re-upgrade on a copy of the real pre-m12 DB;
- 24 H2 tests and 120 full tests passing.

Do not regress these behaviors.

## 3. Remaining reproduced failures

Codex reproduced all of these despite FK enforcement being enabled:

```text
User.reporting_unit_id = 999999              -> accepted
Organization.reporting_unit_id = 999999      -> accepted
PORT_STAFF belonging to Port A creates an
import whose reporting_unit is Port B         -> accepted
```

Additional gaps:

- `reviewed_by_user_id` is not tenant validated;
- historical audit events have no ReportingUnit scope;
- `_verify_tenant_schema` checks only child → import composites and can miss a
  missing revision, metric → row, cargo → call or link → call constraint.

## 4. Prohibited actions

- Do not begin H3/H4.
- Do not implement parser, upload API, dashboard, exporter or UI.
- Do not commit or push.
- Do not use `git add .`.
- Do not touch, restore, downgrade, stamp or migrate `data/cang_vu.db`.
- Do not modify any backup database.
- Do not stage/commit workbooks, renders, databases or secrets.
- Do not modify CVF core.
- Do not mark H2 closed.

All migration tests must use fresh temporary databases or disposable copies.

## 5. Replace soft tenant columns with FK-backed memberships

Remove the unvalidated plain integer fields:

- `User.reporting_unit_id`
- `Organization.reporting_unit_id`

Replace them with FK-backed association tables, using equivalent names such as:

### `reporting_unit_users`

- `reporting_unit_id` → `reporting_units.id`, non-null;
- `user_id` → `users.id`, non-null;
- optional membership role/scope fields only if genuinely needed;
- unique/composite primary key prevents duplicate membership;
- deletion behavior must be explicit and safe.

### `reporting_unit_organizations`

- `reporting_unit_id` → `reporting_units.id`, non-null;
- `organization_id` → `organizations.id`, non-null;
- unique/composite primary key prevents duplicate membership;
- deletion behavior must be explicit and safe.

Many-to-many membership is acceptable and preferable for future multi-port use:
a staff user or shipping company may legitimately interact with more than one
port, but every operation still uses one explicit active reporting unit.

Platform ADMIN may have no membership. Absence of membership must never be
interpreted as automatic access to every port without an explicit platform
context.

Migration requirements:

- no hardcoded/backfilled Tân Thuận row;
- existing users/organizations remain unchanged and initially have no
  memberships;
- downgrade drops only the two membership tables and H2 structures;
- no soft integer tenant columns remain in model or corrected migration;
- invalid/nonexistent user, organization or reporting-unit IDs must fail by FK.

## 6. Fail-closed actor and reviewer authorization foundation

Extend `backend/historical.py` with explicit validators. Equivalent API names
are acceptable, but behavior must be clear and separately testable.

### Import/revision actor validation

For a target `reporting_unit_id`:

- PORT_STAFF must have membership in that reporting unit;
- tenant-local ADMIN must have membership in that reporting unit;
- CUSTOMER is rejected;
- inactive user is rejected;
- missing user/unit is rejected;
- a platform ADMIN with no tenant membership is allowed only when the caller
  supplies an explicit platform/tenant context flag or context object;
- platform ADMIN access must never arise merely because membership is NULL.

The validator must cover creation, revision selection and supersession actor
decisions. H2 does not need endpoints, but H3 must have one safe function to
call.

### Reviewer validation

Before assigning `HistoricalVesselLink.reviewed_by_user_id` or accepting a
manual review decision:

- reviewer must be active;
- reviewer must be PORT_STAFF/ADMIN;
- reviewer must be authorized for the link/import reporting unit under the
  membership/platform-context rules above;
- cross-port reviewer is rejected.

Do not rely on comments or future API code. Add the H2 service validators and
negative tests now.

The database may retain ordinary user FKs for actor/reviewer because platform
ADMIN is an exception that is difficult to encode in one composite FK. The
service boundary must nevertheless be fail-closed and fully tested.

## 7. Candidate-vessel membership validation

Update `validate_vessel_link_tenant` to use
`reporting_unit_organizations`, not a soft
`Organization.reporting_unit_id` column.

Rules:

- missing vessel or organization: reject;
- no Organization membership in the target reporting unit: reject;
- membership in another unit only: reject;
- membership in the target unit: allow;
- unresolved candidate (`candidate_vessel_id is None`): allow as pending;
- an Organization may have memberships in multiple ports; a vessel is valid for
  any port in which its Organization has a real FK-backed membership.

## 8. Tenant-scoped audit

Add a nullable `reporting_unit_id` FK to `AuditEvent` or an equivalent durable
tenant-scoped audit design.

Requirements:

- existing audit events remain valid with NULL reporting unit;
- every historical import/revision/review audit must carry the affected
  reporting unit;
- `organization_id` continues to mean customer Organization and must not be
  overloaded with a Port ID;
- audit remains attributable after normal application queries and is filterable
  by reporting unit;
- no raw workbook values or sensitive payloads in audit summaries.

Update `backend.database.audit` to accept an optional `reporting_unit_id` and
store it. Existing callers must remain backward compatible.

Add tests proving:

- existing non-historical audit without reporting unit still works;
- historical audit stores the correct reporting unit;
- nonexistent reporting unit is rejected by FK;
- an audit for Port B is not mislabeled with customer Organization B.

## 9. Complete schema-drift verification

Keeping `_has_table` guards is acceptable only because the baseline migration
uses current `Base.metadata.create_all`. The post-verification must validate the
full tenant-critical schema, not just child → import.

At minimum verify named constraints/relationships for:

- ReportingUnit table and identity;
- reporting-unit user membership FKs and uniqueness;
- reporting-unit organization membership FKs and uniqueness;
- import → ReportingUnit;
- import self-revision composite FK;
- each historical child → import composite FK;
- metric → row composite FK;
- cargo → port-call composite FK;
- vessel-link → port-call composite FK;
- vessel-link `import_id` non-null;
- required idempotency and identity unique constraints;
- critical CHECK constraints used for status and blank/zero behavior;
- AuditEvent → ReportingUnit FK if that design is selected.

Implement reusable inspection helpers if useful. Fail with a precise message
naming the missing table/column/constraint.

Add at least one test that constructs or simulates a drifted schema missing a
secondary composite constraint (for example cargo → port call or revision self
FK) and proves verification rejects it. Merely inspecting the correct schema is
not enough.

## 10. Operational database blocker

The operational database remains stamped with the rejected old m12. Do not
touch it during this correction.

Preserve this handoff statement:

```text
Operational DB is stamped with rejected m12 and requires a separate,
Codex-reviewed reconciliation step after the corrected migration is accepted.
```

Do not claim operational migration success. Only temp/copy rehearsal is valid.

The reviewer-created disposable copy
`data/review_h2_corrected_migration.db` is ignored and must not be staged. Do
not treat it as operational evidence or source data.

## 11. Required negative tests

Add tests that actually attempt and reject:

1. membership with nonexistent reporting unit;
2. membership with nonexistent user;
3. membership with nonexistent Organization;
4. PORT_STAFF A acting on import B;
5. tenant ADMIN A acting on import B;
6. CUSTOMER acting on historical import;
7. inactive actor;
8. platform ADMIN without explicit context;
9. cross-port reviewer;
10. candidate vessel whose Organization has only another port membership;
11. historical audit with nonexistent reporting unit;
12. schema drift missing a secondary composite constraint.

Also add positive tests for:

- valid PORT_STAFF membership;
- valid tenant ADMIN membership;
- platform ADMIN with explicit context;
- Organization belonging to multiple ports;
- correct reporting-unit historical audit.

Retain all prior cross-tenant, migration, cascade, ATB/ATD and blank/zero tests.

## 12. Verification

Run only on tests/temp copies:

```powershell
python -m alembic heads
python -m pytest -q tests/test_historical_import.py
python -m pytest -q
git diff --check
git status --short
```

Report:

- migration revision chain;
- membership-table constraints;
- actor/reviewer validator rules;
- audit tenant scope;
- number and names of new negative tests;
- `PRAGMA foreign_keys` and `foreign_key_check` for test DB;
- confirmation operational DB and backups were not modified;
- confirmation workbooks/databases remain untracked/ignored;
- confirmation H3/H4 were not started.

## 13. Handoff and delivery

Append an R2 correction section to `docs/AGENT_HANDOFF.md`. Preserve previous
history and explicitly state that H2 remains pending Codex review round 3.

Do not commit. Stop after producing a concise implementation report. Wait for
Codex review round 3.
