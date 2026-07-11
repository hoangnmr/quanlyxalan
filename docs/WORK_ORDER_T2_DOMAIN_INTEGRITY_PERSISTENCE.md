# Work Order T2 — Domain Integrity and Persistence

## Control block

- Work order: `WO-KBCV-T2-20260711`
- Status: CLOSED — Gate 2 evidence recorded in `docs/AGENT_HANDOFF.md`
- Depends on: T1 corrective commit `0215b43`
- Risk: R2 / Priority: P0
- CVF phase on assignment: BUILD
- External APIs and production data: OUT OF SCOPE

## Objective

Make domain rules, workflow state, database transactions and schema evolution
deterministic and auditable. Remove runtime schema creation as a production
migration mechanism and establish a safe path from the current SQLite pilot to
later PostgreSQL operation.

## Authorized scope

- Pydantic request/response models and domain validation.
- SQLAlchemy models, relationships, repositories/services and transactions.
- Alembic baseline and forward migrations.
- Workflow state machine, immutable snapshots and audit records.
- Tests, ADRs, API contract, migration/runbook and handoff.

## Out of scope

- Real production data migration or PostgreSQL cutover.
- File/import/report hardening assigned to T3.
- Deployment infrastructure assigned to T4.
- External integrations assigned to T6.
- Deleting `data/cang_vu.db` to resolve migration failures.

## Required tasks

1. Inventory every write endpoint and define one transaction boundary per
   operation. Remove helper-level commits that can leave partial state.
2. Standardize API errors for validation, not-found, duplicate, conflict and
   concurrency failure; ensure rollback on all failed writes.
3. Replace remaining untyped dictionaries and ad-hoc payload parsing with
   Pydantic v2 models; migrate deprecated `orm_mode`/class Config usage.
4. Validate enums, required strings, numeric bounds, ETA < ETD, date ranges,
   registration/reference formats and cross-field rules.
5. Model the workflow as one server-side transition table. Require valid role,
   current state, action-specific note/permit fields and submitted snapshots.
6. Prevent ordinary edits after submission; define resubmission after
   `CHANGES_REQUESTED` and preserve event history.
7. Complete SQLAlchemy relationships, cascades, unique/check constraints,
   timezone-aware timestamps and optimistic concurrency/version field.
8. Establish a full Alembic baseline for all current tables, then layer T1/T2
   changes in a reproducible chain. Production startup must not call
   `Base.metadata.create_all()`.
9. Add correlation id to request context and persist actor id, organization id,
   action, entity, timestamp and correlation id in append-only audit evidence.
10. Document SQLite pilot limits and the future PostgreSQL cutover contract.

## Required tests

- Boundary and malformed input tests for every write model.
- Duplicate keys, missing entities and stale-version conflicts.
- Forced database error proves full rollback with no partial organization,
  declaration, event or attachment metadata.
- Complete workflow transition table including negative transitions.
- Submitted snapshot immutability and approved correction/resubmission path.
- Audit event completeness and correlation-id propagation.
- Alembic upgrade from T0/T1 copies, downgrade rehearsal where safe, and fresh
  database bootstrap using migrations only.
- Full T0/T1 regression suite.

## Gate 2 acceptance

1. All tests PASS and `git diff --check` PASS.
2. Fresh database and T1 database copy both upgrade to head successfully.
3. Failed writes roll back atomically.
4. Invalid or skipped state transitions cannot mutate data.
5. Submitted records cannot be silently overwritten.
6. Audit records contain authoritative actor and correlation information.
7. Runtime code does not use `create_all()` as a production migration path.
8. Migration and rollback evidence is recorded without real customer data.
9. CVF Doctor PASS and human R2 review approves Gate 2.

## Stop and escalate

Stop if a migration can lose/merge existing records, if signed business rules
are ambiguous, if a destructive database operation is required, or if the
working tree contains conflicting unrelated changes.

## Delivery report

Report baseline/final commits, schema and transition changes, exact test
commands/counts, migration matrices, rollback evidence, residual risks and
final Git/Doctor status. Do not mark CLOSED before a committed reviewer-approved
Gate 2.
