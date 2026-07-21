# Claude correction order — H2 historical/TOS foundation

Date: 2026-07-18  
Reviewer: Codex  
Phase: BUILD  
Risk: R2  
Status: H2 REJECTED — CORRECTION REQUIRED; H3/H4 NOT AUTHORIZED

## 1. Instruction

Correct the current uncommitted H2 implementation in this repository. Work
only in the existing working tree. Do not ask the user to copy/paste the review;
this file is the authoritative correction order.

Read before editing:

- `AGENTS.md`
- `.cvf/manifest.json`
- `.cvf/policy.json`
- `../WORKSPACE_RULES.md`
- `docs/AGENT_HANDOFF.md`
- `docs/HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md`
- `docs/HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md`
- `docs/historical_tos_mapping_draft.json`

## 2. Reviewer findings

Codex independently reproduced the following defects:

1. `Organization` currently represents a customer company, not a Port/reporting
   unit. PORT_STAFF users commonly have no `organization_id`.
2. A child carrying reporting unit B can reference an import owned by reporting
   unit A.
3. An import owned by A can set `superseded_by_import_id` to an import owned by
   B.
4. Metric → row/import, cargo → call/import and vessel-link → import/call/vessel
   relationships have the same tenant-consistency gap.
5. The application SQLite engine reports `PRAGMA foreign_keys = 0`; declared
   foreign keys and database cascades are not enforced.
6. The new tests do not contain the required negative cross-tenant insertions.
   The cascade test proves ORM cascade only.
7. Both `HistoricalVesselLink.import_id` and `port_call_id` are nullable, so an
   untraceable link can be created.
8. `_has_table` migration guards can silently accept a partial or drifted
   schema.
9. The operational database was upgraded to rejected revision
   `m12f0f000012`, contrary to the instruction to rehearse only on disposable
   copies.

Independent reviewer results:

- H2 tests: 11 passed.
- Full regression: 107 passed.
- Tenant isolation: failed by direct reproduction.
- SQLite FK enforcement: failed (`foreign_keys = 0`).

Passing tests do not override these defects.

## 3. Prohibited actions

- Do not begin H3/H4: no parser, upload API, dashboard, export or UI work.
- Do not commit or push.
- Do not use `git add .`.
- Do not stage or commit real workbooks, renders, databases, backups or secrets.
- Do not modify, downgrade, restore, stamp or migrate `data/cang_vu.db` again.
- Do not modify any backup database.
- Do not modify CVF core.
- Do not retain the assumption `Organization = ReportingUnit`.
- Do not mark H2 closed.

All migration rehearsals must use newly created temporary databases or
disposable copies.

## 4. Correct tenant model

Introduce a distinct entity such as `ReportingUnit`/`PortTenant`, stored in a
`reporting_units` table.

The boundaries are:

- ReportingUnit/PortTenant: a Port that purchases and operates the product.
- Organization: a customer company that owns vessels and declarations.
- User: belongs to a reporting unit and/or customer organization according to
  role.
- Historical import/report: belongs to one reporting unit, never implicitly to
  a customer organization.

Cảng Tân Thuận is the first reporting unit but must not be hardcoded in a model,
migration, default row or parser rule.

Schema must be able to represent:

- a customer Organization belonging to a ReportingUnit;
- a PORT_STAFF user belonging to a ReportingUnit;
- a tenant-local ADMIN belonging to a ReportingUnit;
- a platform-level administrator with no permanently selected unit, with future
  cross-port actions requiring an explicit context;
- every historical import belonging to exactly one ReportingUnit.

If `reporting_unit_id` is added to `organizations` or `users`, preserve backward
compatibility. Do not hardcode/backfill existing records to Tân Thuận. Document
which fields remain nullable during migration and why.

## 5. Enforce tenant consistency

Do not rely on unrelated single-column foreign keys plus repeated
`reporting_unit_id` values. Prefer normalized ownership and composite foreign
keys/unique keys.

At minimum, reject:

- row B → import A;
- metric B → import or row A;
- port call B → import A;
- cargo B → import or port call A;
- vessel link B → import or port call A;
- revision A → replacement B.

Revision lineage should use an equivalent of:

```text
(superseded_by_import_id, reporting_unit_id)
  -> historical_report_imports(id, reporting_unit_id)
```

Add the necessary unique candidate keys for composite references.

Metric ownership must guarantee that `row_id`, `import_id` and reporting unit
agree. Cargo ownership must guarantee that `port_call_id`, `import_id` and
reporting unit agree.

`HistoricalVesselLink.import_id` must be non-null. `port_call_id` may be null
for a link originating from another imported report row, but when present it
must belong to the same import/reporting unit.

A candidate Vessel is valid only when its customer Organization belongs to the
same ReportingUnit. If this multi-hop rule cannot be enforced portably with a
database constraint, implement the best database boundary plus fail-closed
model/service validation and real negative tests. Document the remaining
limitation.

## 6. Enable SQLite foreign keys

Enable `PRAGMA foreign_keys=ON` for every application SQLite connection through
a SQLAlchemy connection event. Apply equivalent enforcement to Alembic and test
engines.

Required evidence:

- application/test connection reports `PRAGMA foreign_keys = 1`;
- `PRAGMA foreign_key_check` is clean on test databases;
- invalid foreign keys raise `IntegrityError`;
- database-level cascade is tested by direct SQL deletion, not ORM cascade.

Before proposing this setting for the operational database, run only the
read-only `PRAGMA foreign_key_check` and report the result. Do not repair or
mutate operational data in this correction turn.

## 7. Correct migration m12

Revision `m12` is uncommitted and may be redesigned in the working tree, but it
must only be exercised on fresh/temp databases.

- Remove `_has_table` guards that silently skip existing drifted tables.
- Migration must create the exact approved schema or fail clearly.
- Remove the artificial test that stamps back to l11 while retaining m12
  tables and calls that migration idempotency.
- Confirm one Alembic head.
- Rehearse fresh upgrade, downgrade and re-upgrade on a disposable database.
- Downgrade must remove only the H2 schema/columns.
- Do not hardcode or seed Tân Thuận.
- Do not change live facts while testing migration preservation.

The operational DB is already stamped with the rejected m12. Do not touch it.
Record this exact blocker in the handoff:

```text
Operational DB is stamped with rejected m12 and requires a separate,
Codex-reviewed reconciliation step after the corrected migration is accepted.
```

## 8. Provenance and checks

Every historical fact must trace to one import. Preserve workbook checksum,
sheet, row/cell, raw/sanitized source value, mapping version, transformation
version and validation state as applicable.

Keep ATB and ATD as separate facts. Never rename ATB to ATA. Keep blank, zero
and invalid as separate states.

Add portable constraints where appropriate:

- `revision_no >= 1`;
- accepted/rejected/review counts >= 0;
- source size >= 0;
- supported TEU factor or null when under review;
- status/state values restricted to approved sets;
- value/state consistency where practical.

Do not turn H2 into a parser implementation.

## 9. Required tests

Add or correct tests proving:

1. Fresh database upgrades to the single Alembic head.
2. A pre-H2 database is seeded with real Organization/User/Vessel/Declaration
   rows before upgrade.
3. Upgrade preserves all seeded live values.
4. Downgrade preserves all seeded live values and removes only H2 structures.
5. Re-upgrade succeeds.
6. ReportingUnit is a distinct entity from Organization.
7. `PRAGMA foreign_keys == 1`.
8. `PRAGMA foreign_key_check` returns no rows on test databases.
9. Same checksum is permitted in two reporting units.
10. Exact duplicate in one reporting unit is rejected.
11. Every cross-tenant relationship listed in section 5 is rejected.
12. Cross-tenant revision is rejected.
13. An orphan vessel link without an import is rejected.
14. Cross-reporting-unit candidate vessel linking fails closed.
15. Database cascade works through direct SQL deletion.
16. Blank, zero and invalid remain distinct.
17. ATB and ATD remain distinct and no ATA field is introduced.
18. Existing regression tests still pass.

A test named tenant isolation must perform a forbidden cross-tenant operation
and assert an `IntegrityError` or explicit fail-closed validation. Merely
creating records for two tenants is insufficient.

## 10. Handoff correction

Append a correction disposition to `docs/AGENT_HANDOFF.md`:

- H2 remains pending Codex review.
- Withdraw the earlier unqualified tenant-isolation claim.
- State that the operational DB is stamped with rejected m12 and was not
  modified further during correction.
- Report only evidence actually exercised by tests.
- Preserve prior handoff history; do not erase it.

## 11. Verification commands

Run against temporary/test databases only:

```powershell
python -m alembic heads
python -m pytest -q tests/test_historical_import.py
python -m pytest -q
git diff --check
git status --short
```

Also report:

- Alembic revision chain;
- `PRAGMA foreign_keys` and `foreign_key_check` results;
- number and names of negative cross-tenant tests;
- confirmation that the operational DB was not modified again;
- confirmation that real workbooks remain untracked.

## 12. Delivery

Do not commit. Stop after producing a concise implementation report containing:

- corrected ReportingUnit architecture;
- tenant constraint strategy for every relationship;
- migration upgrade/downgrade results;
- foreign-key enforcement results;
- full test results;
- remaining limitations;
- final `git status --short`;
- confirmation that H3 was not started.

Wait for Codex review round 2.
