# Claude correction order R3 — close remaining H2 authorization gaps

Date: 2026-07-18  
Reviewer: Codex  
Phase: BUILD  
Risk: R2  
Status: H2 REJECTED AFTER REVIEW ROUND 3; H3/H4 BLOCKED

## Scope

Fix only the two authorization defects below. Preserve the passing R2 schema,
membership tables, composite foreign keys, tenant-scoped audit, migration and
schema-drift verification.

Do not commit, push, start H3/H4, touch `data/cang_vu.db`, modify backups or
stage workbooks/databases.

## Defect 1 — tenant ADMIN can impersonate platform ADMIN

Codex reproduced:

```text
ADMIN has membership in Port A
+ platform_context=True
-> import/review in Port B is allowed
```

Correct `backend/historical.py` authorization rules:

1. If the user has membership in the target ReportingUnit, allow according to
   the permitted role.
2. If the user lacks target membership, platform override is allowed only when:
   - `user.role == "ADMIN"`;
   - `platform_context is True`;
   - the user has **zero ReportingUnit memberships across the whole system**.
3. An ADMIN who belongs to any reporting unit is tenant-local and cannot use
   `platform_context=True` to access a different unit.
4. CUSTOMER, inactive user, missing user and disallowed role remain rejected.
5. Apply the same rule to both import/revision actor authorization and reviewer
   authorization.

Do not infer platform status solely from the caller-provided boolean. The user
must also have no rows in `reporting_unit_users`.

## Defect 2 — inactive ReportingUnit still accepts operations

Codex reproduced:

```text
ReportingUnit.is_active = 0
PORT_STAFF has valid membership
-> import is allowed
```

Authorization must load the ReportingUnit and reject when:

- the unit does not exist; or
- `is_active` is not active (`1`).

This rule applies before membership/platform override and covers both actor and
reviewer validation. A platform ADMIN must not override an inactive unit.

Use a clear error message distinguishing missing and inactive reporting units.

## Required tests

Add negative tests that perform and reject:

1. tenant ADMIN in Port A + `platform_context=True` acting on import Port B;
2. tenant ADMIN in Port A + `platform_context=True` reviewing Port B;
3. PORT_STAFF acting on an inactive ReportingUnit;
4. reviewer acting on an inactive ReportingUnit;
5. platform ADMIN with no memberships + explicit context acting on an inactive
   ReportingUnit.

Retain positive tests proving:

- tenant ADMIN/PORT_STAFF may act within a unit where they have membership;
- a true platform ADMIN with zero memberships and explicit context may act on
  an active unit;
- platform ADMIN without explicit context is rejected.

Run:

```powershell
python -m pytest -q tests/test_historical_import.py
python -m pytest -q
python -m alembic heads
git diff --check
git status --short
```

Do not run Alembic upgrade/downgrade against the operational database. No new
migration should be necessary for these service-layer corrections.

## Handoff

Append a concise R3 correction record to `docs/AGENT_HANDOFF.md`:

- exact authorization condition implemented;
- names/results of the five new negative tests;
- full regression result;
- operational database and backups not modified;
- H3/H4 not started;
- H2 pending Codex review round 4.

Do not commit. Stop and wait for Codex review round 4.
