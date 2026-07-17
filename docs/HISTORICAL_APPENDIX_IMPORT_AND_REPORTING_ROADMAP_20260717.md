# Roadmap — Historical Appendix Import and Reporting

Status: INTAKE — SAMPLE WORKBOOKS REQUIRED; BUILD NOT AUTHORIZED
Date: 2026-07-17
Project: Khai-bao-Cang-vu-recovery-ux
Workstream: Historical PL.01/PL.02/PL.03 import and dashboard
Risk level: R2

## 1. Outcome

Import old official PL.01, PL.02 and PL.03 workbooks into one controlled
historical reporting store so the Port can build a separate historical
dashboard before enough new declarations exist in the application.

Historical appendix rows are report facts as originally reported. They are not
synthetic declarations, do not enter the declaration approval workflow and do
not overwrite canonical vessel, crew or customer master data.

## 2. Product boundary

The central operational database remains the system of record, but historical
imports use dedicated tables and provenance:

- Live operations: `Declaration` and cargo snapshots, included only under the
  approved workflow rules.
- Canonical master: Organization, Vessel, VesselOperatingProfile and CrewMember.
- Historical reports: immutable source files, imported rows and reported
  metrics from old appendices.
- Dashboard: may display historical, live or carefully reconciled combined
  projections, with the source always visible.

Out of scope unless separately approved:

- Reconstructing declarations from aggregate reports.
- Automatically setting any declaration to `APPROVED`.
- Using historical throughput to overwrite vessel capacity or current master
  facts.
- Silently combining overlapping historical and live periods.
- Importing arbitrary customer Excel without a mapped appendix type/version.

## 3. Locked principles

1. Preserve the original file checksum, filename, sheet, row and cell evidence.
2. Preview and validate before commit; rejected rows retain safe error details.
3. Reimporting the same file and mapping version is idempotent.
4. A corrected file creates a traceable revision; it never silently mutates the
   prior import.
5. Vessel registration may create a controlled link to a canonical Salan, but
   historical import never overwrites the Salan master.
6. Missing and measured zero remain distinct.
7. PL.02 selected-month and year-to-date values are stored separately. YTD
   columns from multiple monthly reports must never be summed together.
8. The combined dashboard requires explicit overlap rules and shows provenance.
9. Raw operational workbooks, database snapshots and personal data are not
   committed to Git. Only sanitized mappings and evidence may be committed.
10. No parser is declared ready until actual workbook variants have been
    inspected and rendered with the Spreadsheets skill.

## 4. Decisions required before BUILD

| ID | Decision | Required owner answer |
|---|---|---|
| HDEC-01 | Sample inventory | Provide at least one real workbook for each PL.01, PL.02 and PL.03, including older layout variants if they differ |
| HDEC-02 | Reporting tenant/unit | Identify which Port/reporting unit owns each file and whether one workbook may contain multiple units |
| HDEC-03 | Period source | Confirm where month/date range is read when the workbook title or filename is incomplete |
| HDEC-04 | Revision rule | Decide whether a corrected appendix supersedes an earlier version or both remain selectable |
| HDEC-05 | Overlap rule | Decide whether live approved data or imported historical data wins when both cover the same period |
| HDEC-06 | PL.01 meaning | Confirm whether old PL.01 rows are planned activity, actual activity or mixed by period/version |
| HDEC-07 | PL.02 baseline | Confirm that monthly values drive trends and YTD values are reconciliation snapshots, not additive monthly facts |
| HDEC-08 | PL.03 identity | Approve normalized registration matching and manual review for missing/ambiguous registrations |
| HDEC-09 | Access and retention | Define which roles may import, approve, replace, view and delete historical batches |

Unanswered items remain `NEEDS CONFIRMATION`; the implementation must not infer
them from a single workbook.

## 5. Candidate data model

Exact columns are finalized in DESIGN after sample audit. The minimum model is:

### `historical_report_imports`

- appendix kind and detected template/mapping version;
- reporting unit/tenant and reporting period;
- source filename, checksum, size and source sheet list;
- import/revision status, superseded import reference and reason;
- actor, timestamps, accepted/rejected counts and mapping receipt.

### `historical_report_rows`

- import id, source sheet, source row and appendix row identity;
- optional controlled link to canonical vessel id and normalized registration;
- raw sanitized row payload plus mapped dimensions;
- validation status, warning/conflict state and provenance receipt.

### `historical_report_metrics`

- row/import id, metric code, direction/category and unit;
- value class: selected-period, YTD, reported total or descriptive text;
- numeric value or text value, blank/zero state and source cell;
- mapping version and reconciliation status.

The implementation may use equivalent normalized tables, but it must preserve
these ownership and evidence boundaries.

## 6. Appendix import contracts

### PL.01

- Store each source row as a historical PL.01 fact for its reported period.
- Preserve planned/actual semantics exactly as confirmed by HDEC-06.
- Link registration to a canonical vessel only when unambiguous.
- Do not create a declaration or infer approval history.

### PL.02

- Store selected-month metrics and reported YTD metrics as different value
  classes.
- Monthly dashboard trends use selected-month values.
- Reported YTD is used for reconciliation against the accumulated monthly
  history; mismatches enter a review queue.
- Never sum January-to-July YTD with January-to-August YTD.

### PL.03

- Store each reported vessel row and all 35 mapped columns for the source
  period/version.
- Preserve cargo categories, tons, TEUs, empty TEUs, passenger values, ports,
  dates and `Đại lý PTND` as reported.
- Do not split aggregate PL.03 rows back into unknown calls.

## 7. Dashboard contract

The dashboard must expose the data source:

- `Historical imported`: only historical report facts.
- `Live approved`: only eligible declarations.
- `Combined`: enabled only after overlap reconciliation.

Required views:

- import coverage by appendix, year, month and reporting unit;
- selected-period tons, TEUs, calls/passenger metrics when the source appendix
  legitimately provides them;
- PL.02 monthly trend and YTD reconciliation;
- PL.03 vessel/category history and source-file drill-down;
- unresolved vessel links, mapping warnings and superseded revisions;
- completeness indicators so a missing appendix is not displayed as numeric
  zero activity.

Combined queries must use an explicit period/source precedence table. A visual
total without its source and coverage status is not acceptable evidence.

## 8. Delivery tranches

### H0 — Workbook inventory and visual audit

Status: BLOCKED ON SAMPLE FILES
Phase: INTAKE

Actions:

- Inventory all supplied workbook variants, sheets and reporting periods.
- Use the Spreadsheets skill, loader runtime and artifact-tool; inspect every
  sheet and render 100% of each used range.
- Record header rows, merges, widths, date/title cells, totals, formulas,
  blank/zero behavior and variant-specific labels.
- Produce a sanitized source inventory and ambiguity list.

Exit gate:

- At least one representative real file per appendix is fully inspected.
- HDEC-01 through HDEC-03 and all layout ambiguities are resolved or explicitly
  versioned.

### H1 — Historical mapping specification

Status: NOT STARTED
Phase: DESIGN

Actions:

- Define canonical historical dimensions/metrics for every supported column.
- Map every supported template version to field, unit, value class and source
  cell/row.
- Lock revision, overlap, vessel-link, blank/zero and PL.02 YTD rules.
- Define preview errors, warnings and acceptance thresholds.

Exit gate:

- Owner approves the historical mapping and HDEC-04 through HDEC-09.
- A migration and acceptance-test plan is approved before BUILD.

### H2 — Schema, migration and provenance foundation

Status: NOT STARTED
Phase: BUILD after H1 approval

Actions:

- Back up the database and add the approved historical import tables.
- Add tenant/role controls, checksum idempotency, revision lineage and audit
  events.
- Rehearse upgrade and rollback on a database copy.
- Ensure no migration changes existing declarations or canonical masters.

Exit gate:

- Upgrade/rollback, constraints, isolation, idempotency and audit tests pass.

### H3 — Parser and import API

Status: NOT STARTED
Phase: BUILD

Actions:

- Implement type/version detection and explicit PL.01/PL.02/PL.03 parsers.
- Provide preview, row/cell mapping evidence, partial acceptance and safe errors.
- Support corrected-file revisions without destructive overwrite.
- Add reconciliation for PL.02 monthly versus reported YTD.
- Add manual review for ambiguous vessel links and classifications.

Exit gate:

- Golden fixtures cover each approved layout version, duplicates, corrections,
  missing period, ambiguous registration, blanks, zeros and malformed files.

### H4 — Import UI and historical dashboard

Status: NOT STARTED
Phase: BUILD

Actions:

- Add an Admin/PORT_STAFF import workspace with appendix type, detected period,
  preview, conflict warnings and commit confirmation.
- Add import history, revision/supersession and source drill-down.
- Add historical/live/combined dashboard filters and coverage indicators.
- Block combined totals when period overlap is unresolved.

Exit gate:

- Role, tenant, preview, correction, overlap and accessibility UAT pass.

### H5 — Spreadsheet regression and reconciliation

Status: NOT STARTED
Phase: REVIEW

Actions:

- Import controlled copies of representative appendices.
- Reconcile workbook source totals to stored facts and dashboard outputs.
- Re-export or render supporting QA artifacts without modifying the source.
- Run full application regression and Spreadsheet visual verification.

Exit gate:

- Source → import receipt → database fact → dashboard totals reconcile for every
  supported appendix/version.
- PL.02 monthly/YTD handling and combined-source overlap tests pass.
- No unresolved high-severity mapping or privacy issue remains.

### H6 — Pilot and operational acceptance

Status: NOT STARTED
Phase: REVIEW → FREEZE only after owner acceptance

Actions:

- Pilot with a bounded historical set and named reporting owner.
- Record rejected files, corrections, performance and reconciliation results.
- Back up before production import and document rollback/replay procedures.
- Update runbook, handoff and release boundary.

Exit gate:

- Owner signs the sanitized acceptance record.
- All committed artifacts exclude raw customer workbooks, databases and personal
  data.
- Tranche is committed before closure; production readiness is claimed only for
  the explicitly accepted appendix versions and periods.

## 9. Test matrix

Minimum automated and visual coverage:

- one valid and one malformed file for each appendix/version;
- duplicate checksum and corrected revision;
- missing/invalid report period;
- blank versus numeric zero;
- PL.02 selected month versus reported YTD;
- registration exact match, normalized match, ambiguous match and no match;
- tenant isolation and CUSTOMER import denial if not authorized;
- partial acceptance and safe error messages;
- source totals versus stored metrics versus dashboard;
- unresolved overlap blocks combined totals;
- full used-range render, merge, width, wrap, border, clipping and column shift.

## 10. Evidence and privacy

- Keep raw historical files in an access-controlled input location outside Git.
- Store only source metadata/checksum and controlled database records required
  by the approved retention policy.
- Sanitize names, registrations, phone numbers and company identifiers in public
  QA fixtures and committed screenshots.
- Never commit `.env`, database files, workbook junctions, runtime paths or
  credentials.
- Record application commit, migration head, mapping version and importer actor
  for every acceptance run.

## 11. Execution order and current hold

`H0 sample audit → H1 owner-approved DESIGN → H2 schema → H3 parser/API → H4 UI/dashboard → H5 reconciliation → H6 pilot acceptance`

Current hold: waiting for representative historical PL.01, PL.02 and PL.03
workbooks and the HDEC decisions. The roadmap authorizes discovery and DESIGN
only. It does not authorize schema, code, database or UI changes.
