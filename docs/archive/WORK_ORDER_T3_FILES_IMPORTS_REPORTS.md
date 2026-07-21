# Work Order T3 — Files, Imports and Reports

## Control block

- Work order: `WO-KBCV-T3-20260711`
- Status: CLOSED — Gate 3 local/pilot evidence recorded in `docs/AGENT_HANDOFF.md`
- Depends on: T2 CLOSED
- Risk: R2 / Priority: P1
- CVF phase on assignment: BUILD
- Real external transmission: OUT OF SCOPE

## Objective

Make attachment handling, Excel imports and Appendix 1/2/3 outputs safe,
repeatable, versioned and verifiable against approved business mappings.

## Authorized scope

- Attachment validation/storage abstraction and quarantine state.
- XLSX parser limits, preview/import workflow and idempotency.
- Report datasets, templates, export jobs and golden-file verification.
- Tests, mapping documents, operational runbooks and handoff.

## Required tasks

1. Enforce request and decompressed-size limits, extension allowlist, magic
   bytes, archive entry count/path safety and compression-ratio limits before
   parsing Office files.
2. Reject encrypted, malformed, macro-enabled or unsupported files according
   to an approved policy. Use hardened XML parsing and prevent external entity,
   formula and zip-bomb abuse.
3. Normalize filenames, store generated object keys, compute checksum, and
   separate `QUARANTINED`, `CLEAN`, `REJECTED` states. No user file may execute
   or be served with unsafe content disposition.
4. Define a malware-scanner adapter. Local tests may use a deterministic fake
   only for component behavior; production readiness requires the approved
   scanner and operational evidence.
5. Add import preview with template version, row number, normalized values,
   warnings/errors and explicit operator confirmation.
6. Enforce row-level schemas and tenant ownership. Use batch transactions with
   a documented all-or-nothing or partial-acceptance policy.
7. Add import idempotency keys/checksums and duplicate resolution rules.
8. Version the source templates and field mappings for vessel, declaration and
   Appendix outputs. Record mapping owner and approval date.
9. Produce deterministic Appendix 1/2/3 datasets and golden files. Add formula,
   TEU, totals, Unicode, date-range and empty-period tests.
10. Introduce bounded asynchronous export for large datasets with status,
    expiry and authorized download; keep small exports synchronous.

## Gate 3 acceptance

1. Malformed, oversized, path-traversal and decompression-bomb samples fail
   safely without excessive resource use.
2. Cross-tenant file/import access is denied and tested.
3. Repeated import does not create unintended duplicates.
4. Preview and final import results reconcile by row and checksum.
5. Appendix 1/2/3 match approved golden datasets and signed field mapping.
6. Quarantine/scanner failure is fail-closed.
7. Full regression suite, `git diff --check` and CVF Doctor PASS.
8. Human business/security review approves Gate 3.

## Stop and escalate

Stop if signed templates/mapping ownership is unavailable, real customer files
are required for tests, malware-scanner authority is missing, or report meaning
would change without business approval.

## Delivery report

Include malicious fixture inventory, parser limits, mapping versions, golden
file hashes, test counts, scanner boundary, residual risks and final commit/
Doctor evidence. Do not enable external sending.
