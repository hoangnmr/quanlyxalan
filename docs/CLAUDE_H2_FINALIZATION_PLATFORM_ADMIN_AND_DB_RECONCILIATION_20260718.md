# Claude final H2 order — platform administration and DB reconciliation

Date: 2026-07-18  
Owner authorization: EXPLICIT  
Phase: BUILD  
Risk: R2  
Target: finalize and commit H2; do not start H3/H4

## 1. Outcome

Complete two owner-approved changes as one controlled H2 finalization:

1. Simplify product roles to:
   - `PLATFORM_ADMIN`
   - `PORT_STAFF`
   - `CUSTOMER`
2. Reconcile the operational SQLite database that is stamped with the rejected
   old m12, using the pre-m12 backup as the clean source, then commit the
   accepted H2 implementation.

The existing account with username `admin` becomes `PLATFORM_ADMIN`. There is no
Tenant Admin role. `PORT_STAFF` performs all tenant/port operations for the
reporting units in which the user has membership.

Read first:

- `AGENTS.md`
- `.cvf/manifest.json`
- `.cvf/policy.json`
- `../WORKSPACE_RULES.md`
- `docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md`
- `docs/AGENT_HANDOFF.md`
- `docs/CLAUDE_H2_CORRECTION_ORDER_20260718.md`
- `docs/CLAUDE_H2_CORRECTION_ORDER_R2_20260718.md`
- `docs/CLAUDE_H2_CORRECTION_ORDER_R3_20260718.md`

Preserve the H2 implementation accepted by Codex review round 4: ReportingUnit,
FK-backed memberships, composite tenant FKs, SQLite FK enforcement,
tenant-scoped audit, schema-drift verification and fail-closed historical
validators.

## 2. Safety boundary

The owner explicitly authorizes a controlled replacement of only:

```text
data/cang_vu.db
```

after every staging and logical-comparison gate below passes.

Do not delete or overwrite:

- any backup database;
- any workbook;
- any source file outside this repository;
- CVF core;
- any database other than the exact operational target above.

Do not push. Do not start H3/H4. Do not import TOS/workbook data.

Stop without replacing the operational DB if any gate fails, including any
logical live-data difference between the current DB and pre-m12 backup.

## 3. Role model

The final role model is:

### `PLATFORM_ADMIN`

- product-wide administration;
- create/activate/deactivate ReportingUnits;
- manage reporting-unit memberships;
- inspect cross-tenant audit and platform configuration;
- manage migrations, backup/integration configuration and tenant identity;
- may perform a tenant operation only with explicit tenant/platform context;
- never combines data from multiple tenants implicitly.

### `PORT_STAFF`

- must have membership in each ReportingUnit operated;
- performs port declaration review/approval and port-register operations;
- performs historical/TOS import, preview, commit, revision resolution and
  report adjustments after H3/H4 implement those surfaces;
- exports tenant reports;
- has no platform-wide tenant-management authority.

### `CUSTOMER`

- remains tenant/customer scoped;
- has no internal TOS/historical import authority.

Remove `ADMIN` from the active role enum and authorization logic. Do not create
`TENANT_ADMIN` or an `admin_scope` field.

## 4. Convert the existing global administrator

The existing operational account is:

```text
username = admin
current role = ADMIN
```

Corrected m12 must migrate all legacy `ADMIN` users to `PLATFORM_ADMIN`. This is
the correct compatibility rule because the application did not previously have
a tenant-local ADMIN role.

Requirements:

- use a role-based data migration (`role='ADMIN' -> 'PLATFORM_ADMIN'`), not a
  password change;
- never log or expose password hashes;
- downgrade may restore migrated `PLATFORM_ADMIN` to legacy `ADMIN` only as
  required for reversible pre-H2 compatibility; document the limitation;
- staging verification must confirm username `admin` is active and has role
  `PLATFORM_ADMIN` after upgrade;
- no tenant membership is required for this platform account;
- no other user may gain platform role by losing membership.

## 5. Update application RBAC consistently

Inspect every use of `ADMIN` in backend, frontend, scripts and tests. Classify
the permission; do not use blind text replacement.

At minimum update:

- `backend/rbac.py` role enum and role verification;
- every `require_roles(...)` declaration;
- authentication/current-user serialization as needed;
- admin-only system/maintenance operations;
- operational endpoints where platform support remains allowed;
- frontend role labels, visibility rules and navigation;
- preview/static frontend mirrors;
- fixtures, bootstrap/admin scripts and tests;
- historical actor/reviewer validators.

Historical authorization rules become:

- `PORT_STAFF`: active user, active ReportingUnit and membership in target;
- `PLATFORM_ADMIN`: active user, active ReportingUnit and explicit
  `platform_context=True`; membership is neither required nor sufficient;
- `CUSTOMER`: rejected;
- legacy `ADMIN`: rejected after migration.

Delete the obsolete tenant-ADMIN/platform-ADMIN inference based on “ADMIN with
zero memberships”. The explicit role now carries platform identity.

Add negative tests proving:

- PORT_STAFF A cannot act/review in Port B;
- PORT_STAFF cannot use platform context to cross ports;
- PLATFORM_ADMIN without explicit context is rejected for tenant operations;
- legacy `ADMIN` is rejected by current role validation;
- CUSTOMER and inactive users remain rejected;
- inactive ReportingUnit rejects both roles.

Add positive tests proving:

- PORT_STAFF with target membership is allowed;
- one PORT_STAFF can hold memberships in multiple ports and explicitly operate
  either;
- PLATFORM_ADMIN with explicit context can operate an active selected port;
- existing `admin` account becomes PLATFORM_ADMIN through migration.

## 6. Pre-reconciliation inventory

Exact files:

```text
Operational DB:
data/cang_vu.db

Clean pre-m12 source backup:
data/backups/cang_vu-20260718-021834-pre-m12-historical.db
```

Before any replacement:

1. Resolve and print the absolute paths.
2. Confirm both paths remain inside this repository's `data` directory.
3. Record SHA-256, size and modified time of both files.
4. Open both read-only and record:
   - `PRAGMA integrity_check`;
   - `PRAGMA foreign_key_check`;
   - Alembic revision;
   - row counts for every application table;
   - 59 Vessel expectation;
   - Declaration count;
   - AuditEvent count;
   - user id/username/role/is_active only (never password hash).

Create an additional immutable timestamped backup of the current operational DB
under:

```text
data/backups/
```

The filename must include `pre-h2-final-reconcile`. Never overwrite an existing
backup. Record its SHA-256 and confirm it matches the current operational DB.

## 7. Logical live-data equality gate

The current operational DB and the pre-m12 backup may differ physically because
the current DB has the rejected old m12 schema. Before using the backup as the
replacement source, prove that their pre-H2/live business data is logically
identical.

Compare every non-H2 application table, excluding only:

- `alembic_version`;
- rejected historical/TOS tables introduced by old m12;
- SQLite internal tables.

For every compared table:

- compare column sets relevant to the pre-H2 schema;
- compare row count;
- compare deterministic ordered logical row hashes or canonical serialized row
  values;
- include users, organizations, vessels, declarations, crew, audit events,
  import jobs, report adjustments, attachments and all other live tables that
  exist.

Required known checks include:

- 59 vessels;
- 0 declarations unless current read-only inventory proves otherwise;
- AuditEvent count and logical content identical;
- the `admin` account exists and is active with legacy `ADMIN` role before
  corrected migration.

If any live table differs, STOP. Do not replace the operational database. Report
the exact table and mismatch without exposing secrets or personal data.

## 8. Build staging database

Create a new uniquely named staging copy under `data/` from the clean pre-m12
backup. Do not use or modify the source backup in place.

Point Alembic to staging only through `TEST_DATABASE_URL` or an equivalent
explicit disposable-database configuration. Confirm Alembic current is
`l11f0f000011` before upgrade.

Apply corrected `m12f0f000012` to staging.

Never run corrected m12 directly against the operational DB, because the
operational DB is already stamped with the rejected revision of the same ID.

## 9. Staging acceptance gate

All checks must pass on staging:

- Alembic current: `m12f0f000012`;
- `PRAGMA integrity_check = ok`;
- `PRAGMA foreign_keys = 1` for the validation connection;
- `PRAGMA foreign_key_check` returns no rows;
- exactly one Alembic head;
- corrected H2 tables, ReportingUnit membership tables, audit tenant FK and
  composite tenant constraints exist;
- rejected old H2 schema is absent;
- historical/TOS tables contain zero imported facts;
- membership tables contain zero rows unless a separately owner-approved
  bootstrap is performed (none is authorized in this order);
- no ReportingUnit/Tân Thuận row is hardcoded or automatically seeded;
- 59 vessels retained;
- declaration and audit counts/content match the clean source;
- all other live table counts and logical hashes match the clean source;
- user `admin` is active and now has role `PLATFORM_ADMIN`;
- no user retains legacy `ADMIN` role;
- no password hash changes.

Run migration downgrade to l11 and re-upgrade on a separate disposable copy of
staging or a second clean staging copy. Confirm live rows and the role
transformation behave as documented. Do not downgrade the accepted staging file
that will replace operational unless it is subsequently rebuilt cleanly from
the pre-m12 backup.

## 10. Test gate before replacement

Run:

```powershell
python -m pytest -q tests/test_historical_import.py
python -m pytest -q
python -m alembic heads
git diff --check
```

The previous baseline was 148 tests; the final count should be 148 or higher.
Any failure blocks replacement and commit.

## 11. Controlled operational replacement

Proceed only after sections 6–10 all pass.

1. Confirm no application/server process holds the operational SQLite file.
2. Re-resolve the exact operational and staging absolute paths.
3. Confirm staging is inside this repository's `data` directory and is not the
   backup source.
4. Confirm the timestamped current-DB backup exists and hash-matches the current
   DB immediately before replacement.
5. Replace only `data/cang_vu.db` with the accepted staging database using a
   recoverable exact-file copy/replace operation. Never use a recursive command,
   glob or broad directory target.
6. Record the resulting operational SHA-256.

Immediately validate the replaced operational DB read-only:

- Alembic `m12f0f000012`;
- integrity `ok`;
- FK check clean;
- 59 vessels;
- expected declarations and audit events;
- corrected H2 schema present and empty;
- `admin` is active `PLATFORM_ADMIN`;
- no legacy `ADMIN` user;
- logical live-data hashes still equal the accepted staging values.

If post-replacement validation fails, stop the application and restore the
timestamped `pre-h2-final-reconcile` backup using the same exact-file safety
checks. Report the rollback; do not continue to commit.

## 12. Final regression and documentation

After successful replacement:

- rerun the complete test suite;
- rerun `git diff --check`;
- update the roadmap:
  - H2 `CLOSED`/accepted;
  - H3 `READY`, not started;
  - role model recorded as PLATFORM_ADMIN/PORT_STAFF/CUSTOMER;
- append final H2 reconciliation evidence to `docs/AGENT_HANDOFF.md`;
- record backup filename, hashes, before/after revision, counts, integrity and FK
  results without secrets or personal data;
- remove obsolete statement that the operational DB remains stamped with the
  rejected m12, while preserving it as historical context in earlier handoff
  sections;
- do not claim production deployment or FREEZE.

## 13. Commit whitelist

Stage only reviewed source/governance artifacts, including as applicable:

- backend Python source;
- corrected Alembic migration;
- tests;
- frontend role-label/visibility changes;
- sanitized roadmap/handoff/audit/mapping/order documents.

Never stage:

- `templates/*.xlsx` operational workbooks;
- `data/*.db`;
- `data/backups/*`;
- staging/review databases;
- outputs/renders;
- `.env`, credentials or secrets.

Use explicit `git add -- <whitelisted paths>`. Do not use `git add .`.

Before commit, inspect:

```powershell
git diff --cached --check
git diff --cached --stat
git status --short
```

Create one local commit after all gates pass:

```text
feat: add tenant-isolated historical import foundation
```

Do not push.

## 14. Delivery report

Report:

- final role matrix and converted account;
- files changed;
- Alembic head;
- current/pre-m12/staging/final hashes and backup filename;
- logical equality result for every compared live table;
- before/after Vessel, Declaration and AuditEvent counts;
- integrity/FK results;
- H2 and full-test results;
- commit hash;
- final `git status --short` proving only real workbooks remain untracked;
- confirmation H3/H4 were not started and nothing was pushed.

If any gate fails, do not replace or commit. Stop with the exact blocker for
Codex review.
