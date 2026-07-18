# Live Data Validation and Post-Pilot Runbook

Status: OPEN — WAITING FOR APPROVED OPERATIONAL DATA
Date: 2026-07-17
Phase: REVIEW
Risk: R2

## 1. Purpose and claim boundary

This runbook records what remains unproven after the canonical-data and
appendix implementation tranche passed automated and synthetic Spreadsheet
gates. It is used when end users begin entering real declarations and enough
records reach `APPROVED` status.

Current implementation evidence is PASS. Live business data is NOT PROVABLE
because the verified operational database has 47 canonical Salan and zero
approved declarations. Do not treat blank activity cells as an exporter defect
until the source declaration, workflow status and operating date are checked.

## 2. Remaining live-data questions

| ID | What remains unproven | Evidence required | Possible owner |
|---|---|---|---|
| LIVE-01 | Real customer declarations enter the correct tenant and reach `APPROVED` | Declaration id, tenant, workflow history and approval timestamp | PORT_STAFF or explicit-context PLATFORM_ADMIN |
| LIVE-02 | Vessel, crew and static fields inherit correctly without overwriting approved activity snapshots | Before/after master values plus approved declaration snapshot | PORT_STAFF |
| LIVE-03 | ATA/ATD or ETA/ETD select the correct reporting month, including cross-month arrival/departure | Source dates and expected inclusion for PL.01/PL.02/PL.03 | Port operations owner |
| LIVE-04 | Real cargo descriptions classify into the intended export/import/domestic/transshipment/transit columns | Original cargo item, expected category and exported cells | Reporting owner |
| LIVE-05 | Full/empty container quantities, tons, passengers and calls distinguish missing from measured zero | Source values and expected blank/zero result | Reporting owner |
| LIVE-06 | `departure_berth`, working port, destination and `Đại lý PTND` retain the approved customer-declared meaning | Approved source fields and PL.01/PL.03 cells | Port operations owner |
| LIVE-07 | PL.02 manual adjustments are authorized, reasoned, auditable and do not alter source declarations | Adjustment id, role, reason, before/after report and audit event | ADMIN |
| LIVE-08 | Multiple declarations for one Salan aggregate into one PL.03 row without losing drill-down traceability | Contributing declaration ids, expected totals/distinct values and exported row | Reporting owner |

## 3. Minimum operational sample

Do not wait for a large database. Start validation when a small controlled set
of approved records covers these cases:

1. One straightforward arrival and departure in the same month.
2. One arrival in month N and departure in month N+1.
3. Two approved declarations for the same canonical Salan.
4. At least one load and one unload cargo item.
5. Container 20-foot and 40-foot values, including at least one empty unit.
6. At least one non-container cargo case with tons.
7. A passenger call with passengers greater than zero and, when business occurs,
   a confirmed passenger call with `passenger_count = 0`.
8. Dedicated working port, departure berth, destination and `Đại lý PTND`.
9. A genuinely missing activity value and a separately measured numeric zero.
10. One controlled PL.02 adjustment performed by PORT_STAFF or ADMIN.

Rare cargo categories such as transshipment or transit remain open until they
occur naturally or the owner approves a controlled UAT record. Do not fabricate
them inside the production database merely to close evidence.

## 4. Validation procedure

For each selected declaration:

1. Freeze the test window and back up the database before investigation.
2. Record declaration id/reference, tenant, vessel registration, workflow
   status and operating timestamps. Do not copy secrets or unnecessary personal
   data into Git artifacts.
3. Ask the reporting owner to write the expected PL.01, PL.02 and PL.03 cells
   before opening the generated workbook.
4. Export through the same web/API path used by end users.
5. Compare source declaration → canonical DB snapshot → API/report projection →
   final workbook cell. Never diagnose from the workbook alone.
6. Run Spreadsheet visual QA on the generated files: used range, merge, width,
   row height, wrap, border, alignment, clipping, column shift and blank/zero.
7. Record PASS/FAIL per declaration and per appendix. Preserve the unmodified
   failing export and reproduction steps.

Appendix-specific checks:

- PL.01: canonical row exists; static fields are present; activity comes only
  from eligible approved declarations; H/O and I/K keep their distinct meaning.
- PL.02: selected month and January-to-month totals reconcile to source calls
  and cargo; no-data stays blank; adjustment delta and audit record reconcile.
- PL.03: one row per canonical Salan; numeric values sum; distinct text/date/
  port/agent values remain chronological and readable in the same cell.

## 5. Evidence packet

Create one dated packet per validation session. Raw operational exports and DB
snapshots stay in an access-controlled local location and must not be committed.
Only sanitized evidence may enter `docs/`.

Minimum packet:

- environment, app commit and migration head;
- sanitized list of declaration ids/references and workflow states;
- report date/month and user role;
- expected-cell matrix approved by the reporting owner;
- unmodified PL.01/PL.02/PL.03 exports;
- machine-readable inspect result and full/focused renders;
- source-to-cell reconciliation table;
- defect log with severity, reproduction and owner;
- database backup/restore reference without credentials or personal data.

Recommended issue fields:

`Issue ID | Declaration reference | Appendix/cell | Expected | Actual | Source evidence | Reproduction | Severity | Suspected layer | Owner | Status`

## 6. Defect triage before code changes

Classify every discrepancy before editing code:

- DATA: source field is missing, inconsistent or entered in the wrong meaning.
- WORKFLOW: declaration is not eligible, wrong tenant, wrong status or not yet
  approved.
- MAPPING: canonical field or report column uses the wrong source/precedence.
- AGGREGATION: month/YTD, multi-cargo or multi-declaration total is wrong.
- EXPORT FORMAT: value is correct but merge, width, wrap, border or print layout
  is wrong.
- UI: the correct field cannot be entered, confirmed or reviewed reliably.

Do not patch the exporter to compensate for bad source data. Do not alter live
data to hide a mapping defect. A code change requires a reproducible failing
case, expected behavior confirmed by the business owner, a regression test and
a new Spreadsheet render when workbook layout is affected.

## 7. Safety and rollback

- Back up before migrations, bulk corrections or import replays.
- Test fixes against a sanitized copy or controlled staging database first.
- Preserve audit history; do not rewrite approved snapshots silently.
- Never commit `.env`, raw database files, customer workbooks, phone numbers,
  personal identifiers or credentials.
- For any schema/data correction, document rollback and reconciliation steps.
- Keep the current passing synthetic fixtures as regression controls; new live
  evidence supplements them rather than replacing them.

## 8. Live-data acceptance gate

Live business evidence may move from NOT PROVABLE to PROVEN only when:

1. The minimum operational sample is available and owner-approved.
2. Source → snapshot → projection → workbook reconciliation passes for all
   represented cases.
3. PL.01, PL.02 and PL.03 visual QA passes on real-data exports.
4. Any defect is fixed with automated regression coverage and re-rendered
   evidence.
5. Tenant/role boundaries and PL.02 adjustment audit are verified.
6. The owner signs off the sanitized acceptance record.

Until then, the implementation tranche remains CLOSED/PASS while the separate
live-data acceptance gate remains OPEN.
