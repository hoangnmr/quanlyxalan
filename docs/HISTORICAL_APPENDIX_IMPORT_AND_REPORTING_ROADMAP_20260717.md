# Roadmap — Historical Appendix Import and Reporting

Status: BUILD — H1 CONTRACT APPROVED; H2 FOUNDATION AUTHORIZED
Date: 2026-07-17
Updated: 2026-07-18
Project: Khai-bao-Cang-vu-recovery-ux
Workstream: Historical PL.01/PL.02/PL.03 and TOS operational import/reporting
Risk level: R2

## 1. Outcome

Import old official PL.01, PL.02 and PL.03 workbooks and approved TOS source
workbooks into one controlled historical reporting store so the Port can build
a separate historical dashboard before enough new declarations exist in the
application. The first TOS source families under audit are Berth call data and
container/cargo handling detail.

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
- Historical TOS operations: normalized port-call and cargo facts derived from
  approved TOS workbook layouts, with source-cell provenance and controlled
  links to the canonical Salan index.
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
11. Filename is provenance metadata, not a parser or query key. Source kind,
    mapping version and reporting period are detected from workbook structure,
    normalized headers, typed values and owner-approved rules; ambiguous files
    require explicit user confirmation.
12. Python backend/worker code performs workbook validation, extraction,
    normalization, joining, aggregation, staging and export. The browser only
    uploads, displays progress and paginated preview, resolves warnings and
    requests confirmation/download.
13. Python export reads normalized database facts, not the original TOS
    workbook on every report request. Official workbook templates and the
    existing deterministic exporters remain the presentation layer.
14. Existing imports for Vessel, Port Salan register, Crew and Declaration and
    existing live-approved report behavior remain separate and backward
    compatible. TOS workbooks must not enter those endpoints by inference.
15. Historical/TOS facts may live in dedicated tables in the same application
    database; they must not create synthetic declarations, mark a declaration
    `APPROVED` or overwrite canonical master facts.
16. Large-file preview is summarized and paginated. The application must not
    send all raw TOS rows back to the browser or issue one database query per
    source row.
17. Header aliases and structural fingerprints are versioned. Column letters
    are evidence for a specific audited layout, not a universal contract.
18. Every derived report value remains traceable to import, workbook, sheet,
    row/cell, mapping version and transformation rule.

## 4. Decisions required before BUILD

| ID | Decision | Required owner answer | Status |
|---|---|---|---|
| HDEC-01 | Sample inventory | Provide representative historical PL.01/PL.02 variants when available | DEFERRED; supplied TOS/PL.03 audit is sufficient for bounded TOS DESIGN |
| HDEC-02 | Reporting tenant/unit | Multi-port product: Cảng Tân Thuận is the first tenant, not a hardcoded product boundary. Every import/report belongs to exactly one authenticated reporting unit; mixed-unit content must be split or reviewed before commit | CLOSED — owner confirmed 2026-07-18 |
| HDEC-03 | Period source | Use TOS ATB to assign a call/reporting month; blank ATB enters review rather than falling back to filename, ATA or ATD | CLOSED — owner confirmed 2026-07-18 |
| HDEC-04 | Revision rule | A corrected/new TOS file creates a revision; on duplicate/overlap PORT_STAFF or ADMIN must choose whether to replace the active revision | CLOSED — owner confirmed 2026-07-18 |
| HDEC-05 | Overlap rule | Matched TOS wins for actual ATB/ATD, berth and cargo; live retains declaration-only facts; one call counts once; uncertain matches enter review | CLOSED — owner confirmed 2026-07-18 |
| HDEC-06 | PL.01 meaning | Confirm old PL.01 planned/actual semantics when historical PL.01 files are supplied | DEFERRED with PL.01 samples |
| HDEC-07 | PL.02 baseline | Monthly values drive trends and reported YTD remains a non-additive reconciliation snapshot | CLOSED for canonical contract; historical variant audit deferred |
| HDEC-08 | PL.03 identity | Controlled normalized candidates plus manual review for missing/ambiguous vessel links | CLOSED — owner confirmed |
| HDEC-09 | Access and retention | PORT_STAFF/ADMIN may upload, review and choose replacement; CUSTOMER has no TOS access; retain historical data/source receipt at least five years | BASELINE CLOSED; post-five-year purge/storage mechanics remain DESIGN details |

Unanswered items remain `NEEDS CONFIRMATION`; the implementation must not infer
them from a single workbook.

### 4.1 Confirmed TOS and product decisions

These owner decisions were clarified during planning on 2026-07-17 and
2026-07-18. The Codex Desktop artifact-tool audit has now verified the supplied
Berth, cargo-detail, Salan and PL.03 layouts. Missing PL.01/PL.02 samples and
the explicit open decisions below remain outside the verified boundary.

| ID | Decision | Confirmed rule | Status |
|---|---|---|---|
| HTOS-01 | Source families | Berth contains port-call/berth timing facts; CHI TIET contains container/cargo handling facts; historical PL workbooks are reported facts/reconciliation sources | CONFIRMED AND AUDITED for supplied variants |
| HTOS-02 | Vessel identity | TOS vessel name links to the canonical Salan register through controlled normalization and manual review when missing or ambiguous; historical import never overwrites the master | CONFIRMED; sample audit found 10 exact, 26 normalized, 4 unmatched and 0 ambiguous Berth links |
| HTOS-03 | PL.03 vessel column | Vessel name maps to PL.03 column B, `Tên PTTND`; PL.03/AI remains `Đại lý PTND` | CONFIRMED AND AUDITED |
| HTOS-04 | Berth default | When one TOS berth code is available, initialize both arrival and departure berth from it; PORT_STAFF/ADMIN may correct the rare berth-shift case with audit provenance | CONFIRMED AND AUDITED for the one-berth sample |
| HTOS-05 | TOS operating time | ATB and ATA are distinct. Historical TOS reports use authoritative TOS ATB for PL.01/J and PL.03/AG, and TOS ATD for PL.01/L and PL.03/AH. Do not rename imported ATB to ATA | CONFIRMED AND AUDITED; legacy PL.03 used inaccurate ETA-derived time |
| HTOS-06 | Candidate join | Berth-to-detail joining uses vessel identity, year and voyage. Exact raw-component match is primary; normalized candidates fail closed when ambiguous | CONFIRMED AND AUDITED; 1,067/1,067 detail rows matched 38 Berth calls exactly; 2 Berth calls had no cargo |
| HTOS-07 | Cargo dimensions | Detail/R is tonnes per container. All weight, including empty-container shell weight, contributes to report tonnes; F/E independently directs TEU to full or empty columns. Size, trade and movement remain separate dimensions | CONFIRMED BY OWNER 2026-07-18; closes `TOS-WEIGHT-01` and empty-weight treatment |
| HTOS-08 | Import runtime | Python backend/worker extracts only needed fields, aggregates and stages results; web UI orchestrates the job and renders paginated preview | CONFIRMED |
| HTOS-09 | Export runtime | Python backend builds canonical report datasets from database facts and uses the existing template exporters for PL.01/PL.02/PL.03 | CONFIRMED |
| HTOS-10 | Flexible detection | Detection and query logic must not depend on filenames. Filename may be used only as provenance or a low-confidence hint requiring confirmation | CONFIRMED |
| HTOS-11 | Product separation | Current operational imports/exports remain; historical/TOS import receives a separate, clearly labelled workflow and data boundary | CONFIRMED |
| HTOS-12 | Report source UX | Reporting exposes explicit `Live approved`, `Historical imported` and reconciled `Combined` sources; unresolved overlap blocks combined totals | CONFIRMED |
| HTOS-13 | Legacy PL.03 time precedence | AG/AH in the supplied filled PL.03 are legacy reported values based on inaccurate ETA-era logic. Preserve them as reported provenance only; when a TOS call is matched, ATB/ATD are authoritative for reconstructed historical reports | CONFIRMED BY OWNER 2026-07-18; closes `TOS-PL03-TIME-01` |
| HTOS-14 | Movement direction | `Trả rỗng`/`Hạ bãi` map to unload; `Lấy nguyên`/`Cấp rỗng` map to load. F/E and domestic/foreign remain independent | CONFIRMED BY OWNER 2026-07-18; closes `TOS-METHOD-01` |
| HTOS-15 | Legacy PL.03 authority | The supplied PL.03 is a manual staff summary and is not the authoritative derivation target. Preserve it for provenance/comparison; code-derived database reports are the future baseline and end-user feedback remains an acceptance input | CONFIRMED BY OWNER 2026-07-18; closes `TOS-PL03-SCOPE-01` as a reproduction blocker |
| HTOS-16 | Period membership | Assign TOS call/reporting month by ATB. Missing ATB enters review; filename, ATA and ATD do not silently replace it | CONFIRMED BY OWNER 2026-07-18 |
| HTOS-17 | Live/TOS merge | TOS supplies actual time, berth and cargo; live supplies declaration-only facts. A matched call counts once and uncertain matching blocks automatic combination | CONFIRMED BY OWNER 2026-07-18 |
| HTOS-18 | Duplicate/revision UX | When a newer TOS file overlaps stored data, PORT_STAFF/ADMIN must explicitly keep existing data, activate the new revision or cancel; no silent overwrite | CONFIRMED BY OWNER 2026-07-18 |
| HTOS-19 | Retention | Retain historical records, provenance and controlled source receipt for at least five years; users may additionally export and retain manual copies | CONFIRMED BY OWNER 2026-07-18 |
| HTOS-20 | Multi-port tenancy | Use one canonical regulatory report model and versioned PL templates for all ports. Scope every source, import, fact, revision, report and export to one tenant/reporting unit. Cảng Tân Thuận is the first deployment; port/TOS-specific differences belong in tenant configuration or versioned source adapters, never in a forked report model | CONFIRMED BY OWNER 2026-07-18; closes HDEC-02 |

### 4.2 Codex Desktop audit evidence and remaining blockers

Evidence:

- `docs/HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md`
- `docs/historical_tos_mapping_draft.json`
- five workbooks, six sheets and 100% of used ranges inspected with
  `@oai/artifact-tool`; thirteen local renders remain outside Git because they
  contain operational data;
- no source workbook was modified; formula and formula-error scans both found
  zero formulas/errors;
- exact source positions are verified for Berth `B/C/E/H/T/W`, Detail
  `C/E/Q/R/T/W`, Salan identity/static fields and PL.03 `A:AI`;
- hidden Detail rows and columns contain data and must be parsed; PL.03
  passenger columns `AA:AB` may be hidden and the footer position is dynamic;
- the supplied filled and blank PL.03 files share the 35-column header schema
  but require separate detected presentation/source versions.

Open/deferred before the complete historical workstream can close:

- representative historical PL.01 and PL.02 variants and their deferred
  HDEC-01/HDEC-06/HDEC-07 variant audit;
- `TOS-PL03-LABEL-01`: retain/version historical `Teus/Tues/Quá cảng`
  spellings separately from corrected canonical labels;
- foreign cargo, unsupported container sizes and invalid-value paths require
  a real sample or sanitized golden fixture.

## 5. Candidate data model

Exact columns are finalized in DESIGN after sample audit. The minimum model is:

### `historical_report_imports`

- appendix kind and detected template/mapping version;
- non-null tenant/reporting-unit id and reporting period; the authenticated
  tenant context binds the import and the filename never determines ownership;
- source filename, checksum, size and source sheet list;
- import/revision status, superseded import reference and reason;
- actor, timestamps, accepted/rejected counts and mapping receipt.

### `historical_report_rows`

- tenant/reporting-unit id, import id, source sheet, source row and appendix row
  identity;
- optional controlled link to canonical vessel id and normalized registration;
- raw sanitized row payload plus mapped dimensions;
- validation status, warning/conflict state and provenance receipt.

### `historical_report_metrics`

- tenant/reporting-unit id, row/import id, metric code, direction/category and
  unit;
- value class: selected-period, YTD, reported total or descriptive text;
- numeric value or text value, blank/zero state and source cell;
- mapping version and reconciliation status.

### `historical_port_calls` (candidate)

- tenant/reporting-unit id, import id, source sheet/row and mapping version;
- raw and normalized vessel/year/voyage identity components;
- optional reviewed canonical vessel link;
- source berth, initialized arrival/departure berth and correction provenance;
- ATB and ATD as typed historical TOS facts;
- validation, ambiguity and reconciliation status.

### `historical_cargo_rows` (candidate)

- tenant/reporting-unit id, import id, source sheet/row and source call key;
- container size, full/empty, domestic/foreign, operation and weight;
- derived TEU and load/unload direction with transformation version;
- weight unit `tonne` and report-tonnage inclusion for both full and empty
  containers; F/E controls the full-versus-empty TEU column independently;
- controlled call link and unmatched/ambiguous status;
- original blank/zero state and cell-level provenance.

### `historical_vessel_links` (candidate)

- tenant/reporting-unit id, raw/normalized TOS identity and candidate canonical
  vessel id;
- match method, confidence, reviewer and timestamps;
- accepted/rejected state and reason;
- no permission to mutate canonical Vessel fields.

The implementation may use equivalent normalized tables, but it must preserve
these ownership and evidence boundaries. Tenant id is part of idempotency,
overlap, vessel-link and report-query keys; identical checksums or identities in
different ports never collide. Official report identity/header fields come from
the selected tenant configuration without forking the canonical PL schema.

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

### TOS Berth call source

- Detect the supported workbook version by normalized header signature and
  structure, not filename.
- Extract only audited identity, voyage, berth, ATB and ATD fields while
  retaining source-cell provenance.
- Initialize arrival and departure berth from the single source berth when
  only one is available; retain a reviewed correction as a separate audited
  value.
- Preserve ATB as ATB. Do not write TOS rows into live Declaration fields.

### TOS cargo/detail source

- Detect the supported workbook version by normalized header signature and
  structure, not filename.
- Preserve size, full/empty, domestic/foreign, weight and operation as separate
  facts before deriving report measures.
- Apply approved rules `20 feet = 1 TEU`, `40 feet = 2 TEU`, `Trả rỗng/Hạ
  bãi = unload`, and `Lấy nguyên/Cấp rỗng = load`; unsupported values enter
  review rather than being guessed.
- Parse Detail/R as tonnes per container and include it in report tonnes for
  both F and E rows. F/E separately controls whether TEU is reported as full or
  empty; an empty container's shell weight is still transported cargo weight.
- Join to an audited Berth call key; unmatched or ambiguous detail remains in a
  review queue and is excluded from confirmed totals.

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

### Import and reporting UX contract

- Always show the active port/reporting unit in import, preview, receipt,
  dashboard and export surfaces. Bind it from the authenticated session; do not
  infer it from the workbook filename.
- One import job belongs to one reporting unit. If content appears to contain
  multiple units, block commit and require separate batches or explicit review;
  never mix their facts in one tenant dataset.
- Tenant switching is explicit and limited to authorized platform-level
  administration. A port's ADMIN/PORT_STAFF cannot inspect or mutate another
  port's imports, files, reports or revisions.
- The Import area separates `Dữ liệu đang vận hành` from `Dữ liệu lịch sử từ
  TOS`; explanatory copy states what each workflow changes and explicitly says
  TOS import does not create or edit declarations.
- Upload follows `choose file → detect → inspect mapping → preview → confirm →
  receipt`. Users are not required to preserve a filename or choose a source
  type before content detection runs.
- Detection shows source kind, mapping version, reporting period and confidence.
  Low-confidence or competing matches require user selection and never commit
  automatically.
- Preview provides summary counts and paginated tabs for valid, review-required
  and rejected rows. Each warning has a concrete resolution action.
- Confirmation names the historical period and states the non-impact on live
  declarations and canonical masters.
- Import history shows source metadata, mapping version, period, actor,
  accepted/rejected counts, revision/supersession and receipt.
- Duplicate/overlapping TOS data presents explicit `Giữ dữ liệu hiện có`,
  `Dùng bản mới` and `Hủy` actions to PORT_STAFF/ADMIN; no default overwrite.
- Source badges include text (`LIVE`, `LỊCH SỬ`, `KẾT HỢP`, `CẦN KIỂM TRA`) and
  do not rely on color alone.
- CUSTOMER cannot access internal TOS import. PORT_STAFF/ADMIN may upload,
  preview, commit and resolve revisions within their own reporting unit. The
  post-five-year deletion/purge policy remains a DESIGN detail; authorization
  must be visible before an action, not only after a 403.

## 8. Delivery tranches

### H0 — Workbook inventory and visual audit

Status: TOS/PL.03 AUDIT COMPLETE — PL.01/PL.02 VARIANT AUDIT DEFERRED
Phase: INTAKE

Actions:

- Inventory all supplied workbook variants, sheets and reporting periods.
- Use the Spreadsheets skill, loader runtime and artifact-tool; inspect every
  sheet and render 100% of each used range.
- Record header rows, merges, widths, date/title cells, totals, formulas,
  blank/zero behavior and variant-specific labels.
- Produce a sanitized source inventory and ambiguity list.
- Audit at minimum the supplied Berth, CHI TIET, historical PL.03, Salan master
  export and current PL.03 template without committing raw workbooks or renders.
- Measure exact/normalized/unmatched/ambiguous Berth-to-detail and
  TOS-to-canonical-vessel match coverage.
- Produce sanitized `HISTORICAL_TOS_WORKBOOK_AUDIT_20260717.md` and
  `historical_tos_mapping_draft.json` artifacts for owner/Codex review.

Completed evidence:

- all five required workbooks and six sheets inspected read-only;
- all used ranges rendered across thirteen local render artifacts;
- exact Berth/detail/register/PL.03 mappings and join coverage recorded;
- sanitized audit and 59-entry mapping draft created and reviewed;
- `TOS-PL03-TIME-01` closed by owner clarification: the legacy PL.03 used
  inaccurate ETA-derived time; authoritative reconstructed time is TOS ATB/ATD.
- `TOS-WEIGHT-01`, `TOS-METHOD-01` and `TOS-PL03-SCOPE-01` closed by owner
  clarification; the remaining full historical H0 work is deferred to future
  PL.01/PL.02 samples. HDEC-02 is closed by the multi-port tenant rule.

Exit gate:

- At least one representative real file per appendix is fully inspected.
- HDEC-01 through HDEC-03 and all layout ambiguities are resolved or explicitly
  versioned.

### H1 — Historical mapping specification

Status: APPROVED BY OWNER — 2026-07-18
Phase: DESIGN

Actions:

- Define canonical historical dimensions/metrics for every supported column.
- Map every supported template version to field, unit, value class and source
  cell/row.
- Lock revision, overlap, vessel-link, blank/zero and PL.02 YTD rules.
- Define preview errors, warnings and acceptance thresholds.
- Define versioned content signatures, header aliases, confidence thresholds
  and manual source-type confirmation. Filename must not be a required match.
- Define canonical report dataset builders shared by live, historical and
  combined export paths without changing the existing live default.

Exit gate:

- Owner approves the historical mapping and HDEC-04 through HDEC-09.
- A migration and acceptance-test plan is approved before BUILD.

### H2 — Schema, migration and provenance foundation

Status: IN PROGRESS — OWNER AUTHORIZED 2026-07-18
Phase: BUILD

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
- Validate archive/security limits, then use a memory-bounded Python extraction
  path that reads only approved fields and stages batch results.
- Implement job/status/paginated-preview/confirm contracts; avoid synchronous
  full-row JSON preview and per-row database lookup.
- Keep original checksum and mapping receipt while making re-import idempotent.

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
- Separate operational import cards from the clearly labelled historical/TOS
  workspace; do not reuse the current Vessel/Declaration import actions.
- Show detected source kind, mapping version, period and confidence before
  confirmation, with actionable unmatched/ambiguous review queues.
- Make the report source (`Live approved`, `Historical imported`, `Combined`)
  explicit and accessible; keep current live behavior as the default.

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
- identical source checksum/call identity in two tenants remains isolated;
- a mixed-reporting-unit workbook is blocked or split before commit;
- active-tenant identity and official report header are consistent from import
  preview through export;
- partial acceptance and safe error messages;
- source totals versus stored metrics versus dashboard;
- unresolved overlap blocks combined totals;
- arbitrary filenames with valid content signatures and misleading filenames;
- structural version detection, low confidence and competing source matches;
- memory-bounded large-file extraction and paginated preview;
- Berth-to-detail exact, normalized, unmatched, ambiguous and duplicate joins;
- one-source-berth default plus reviewed departure-berth correction;
- ATB retained distinctly from ATA and mapped to historical report time;
- live/historical/combined dataset-builder parity through the same exporter;
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

Current move: on 2026-07-18 the owner approved the H1 contract and explicitly
authorized transition to BUILD. Start with H2 schema, migration, provenance,
tenant isolation and acceptance-test foundation; H3 parser/API and H4 UI follow
their ordered gates. Historical PL.01/PL.02 variant audit remains deferred and
does not block the bounded TOS path. Unsupported labels, foreign cargo, sizes
and invalid-value paths remain fail-closed until covered by a real sample or
sanitized golden fixture. This approval does not authorize production rollout,
external transmission or bypass of REVIEW/FREEZE gates.
