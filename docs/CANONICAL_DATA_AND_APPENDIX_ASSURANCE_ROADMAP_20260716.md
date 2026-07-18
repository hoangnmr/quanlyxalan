# Roadmap — Canonical Data and Appendix Assurance

Status: T0–T4 IMPLEMENTATION CLOSED — LIVE BUSINESS VALIDATION REMAINS
Date: 2026-07-16
Updated: 2026-07-17 — incorporated the 67-column mapping and owner decision register
Project: Khai-bao-Cang-vu-recovery-ux
Current phase: REVIEW
Next phase: downstream live-data acceptance or separate T5 upstream proposal
Risk level: R2

## 1. Outcome

Build one governed canonical-data foundation for imported and manually entered
port-operation data, let each application tab read the appropriate projection
from that foundation, and generate PL.01, PL.02 and PL.03 from explicit,
auditable field mappings.

The reusable lessons will be proposed to the public CVF core only after the
downstream design and evidence are stable. Upstream work must happen in a
separate session rooted at the CVF repository; this roadmap does not authorize
cross-repository edits.

## 2. Evidence baseline

The roadmap is based on three complementary reviews:

1. `docs/APPENDIX_TEMPLATE_AUDIT_20260716.md` — static comparison of the
   templates and exporter code.
2. `docs/APPENDIX_EXPORT_VERIFICATION_20260716.md` — Spreadsheet/Document
   inspection of the generated workbooks, including visual workbook renders.
3. `docs/CVF_UPSTREAM_USE_CASE_CANONICAL_DATA_AND_APPENDIX_AUDIT_20260716.md`
   — sanitized proposal for a reusable CVF use case.
4. `docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md` — owner answers,
   decision status, unresolved conflicts and field/UI implications.

Current evidence supports these claims:

- PL.01 has 16 columns and 47 vessel rows; static data is not shifted into the
  activity columns.
- PL.02 has 16 columns and its activity metrics are blank because the verified
  local database has no declarations/events; vessel capacity was not
  fabricated as production.
- PL.03 has 35 columns and 47 vessel rows; inserted rows retain table style and
  no technical `sum_total` field appears.
- Core field ordering and table mapping pass, but full template fidelity does
  not yet pass.

Open Major issues are the missing PL.01 and PL.02 title blocks, the PL.02
`tháng báo cáo` versus `kỳ báo cáo` semantic difference, and the missing PL.03
signature block.

The Canonical Field Mapping now covers all 67 report columns: PL.01 16,
PL.02 16 and PL.03 35. It records data class, canonical source, fallback,
read time, inclusion condition, blank/conflict rule and evidence cell/range.
Code review confirms four additional production-mapping blockers:

| ID | Column/scope | Blocker | Required decision |
|---|---|---|---|
| MAP-01 | PL.01/H | `passenger_count` can fall back into static passenger capacity | Remove cross-class fallback; define required capacity rule for passenger vessels |
| MAP-02 | PL.01/K | `destination_port` is used as departure position | Define whether `working_port` is sufficient or add a dedicated `departure_berth` snapshot |
| MAP-03 | PL.02/C:P | Period uses `declaration_date`; empty activity is initialized as numeric zero | Define operating-date precedence by movement/event and approve blank-versus-zero semantics |
| MAP-04 | PL.03/AI | `company_name` is used without proof that it means agent/operator | Define the business entity and add a dedicated snapshot/relationship if distinct |

Related field gaps are ATA/ATD entry/confirmation, arrival/departure berth,
agent/operator, an explicit passenger-call rule and canonical handling of
missing values versus measured zero.

The project owner answered all seven remaining confirmations on 2026-07-17.
APPX-01 through APPX-04 and MAP-01 through MAP-05 are closed as business
decisions. `REPORT_MAPPING_SPEC.md` is advanced to `KBCV-REPORT-MAP-1.1` with
business rules approved and implementation details pending. PL.03 now has one
row per canonical Salan/vessel and aggregates eligible customer declarations;
T1 must still define deterministic handling for non-additive fields before
BUILD.

## 3. Locked design principles

1. The operational database is the system of record. A README or index is a
   discovery/control plane, not a replacement database.
2. Master data, event data and aggregates are separate data classes:
   - master: organization, vessel, operating profile and crew identity;
   - event: declaration/port call, movement, cargo and passenger facts;
   - aggregate: derived period and year-to-date report metrics.
3. Imported and manually entered values retain source, import job, timestamp,
   validation status and conflict outcome.
4. A blank lower-priority value must not overwrite a validated canonical value.
5. A declaration may prefill from current master data, but submission/approval
   stores an auditable event snapshot.
6. PL.01, PL.02 and PL.03 activity facts come only from eligible approved
   events. Static vessel records must not fabricate calls, cargo, passengers or
   production.
7. Current master values may override stale static snapshot values only where
   the approved report mapping explicitly permits it.
8. Unknown movement or cargo classifications must be surfaced for review; they
   must not silently fall into a valid report column.
9. Tenant scope and role permissions apply to canonical reads, writes and
   report projections.
10. Every readiness statement names its evidence layer: template, generator,
    dynamic export, visual/print QA or live business data.

## 4. Delivery tranches

### T0 — Resolve report-intent and canonical-semantic decisions

Status: CLOSED — OWNER CONFIRMATIONS RECORDED 2026-07-17
Phase: REVIEW

Actions:

- Decide whether each XLSX must reproduce the complete official form or is an
  approved table-only extract.
- Decide whether PL.02 is strictly monthly or supports an arbitrary reporting
  period under a separately approved specification.
- Decide whether PL.03 must always carry the signature block after the last
  dynamic data row.
- Confirm whether the labels inherited from the template (`Tues`, `Quá cảng`)
  are preserved verbatim or corrected through an approved template revision.
- Approve MAP-01 through MAP-04, including the authoritative operating-date
  rule for arrival/departure events and the semantic owner of PL.03/AI.
- Approve whether arrival/departure position is represented by one working
  berth or two dedicated snapshots.
- Approve the rule that missing activity remains blank while a measured or
  explicitly recorded zero remains numeric zero.
- Record MAP-05 as one canonical Salan/vessel row aggregating eligible customer
  declarations.
- Record all seven owner confirmations in
  `docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md`, section 6, and update
  `REPORT_MAPPING_SPEC.md`.
- Complete DOCX page rendering and Excel print-area/page-break review when the
  required desktop/rendering capability is available.

Exit gate:

- **PASSED 2026-07-17:** APPX-01 through APPX-04 and MAP-01 through MAP-05 have
  approved business decisions or documented exceptions.
- **PASSED 2026-07-17:** `KBCV-REPORT-MAP-1.1` identifies product boundaries,
  form fidelity, period rules and permitted deviations.

### T1 — Canonical data contract and index

Status: CLOSED — DESIGN CONTRACT RECORDED; OWNER AUTHORIZED BUILD 2026-07-17
Phase: DESIGN

Deliverables:

- `docs/DATA_PLATFORM_README.md` — purpose, ownership and operating rules.
- `docs/DATA_INDEX.md` — entities, sources, consumers and navigation map.
- `docs/DATA_FIELD_CATALOG.md` — canonical field, type, unit, source priority,
  tenant scope, validation and report consumers.
- `docs/DATA_INHERITANCE_RULES.md` — prefill, snapshot, overwrite, blank and
  conflict rules between tabs.
- A machine-readable source/field manifest suitable for validation tests.
- Adopt section 11 of `docs/APPENDIX_EXPORT_VERIFICATION_20260716.md` as the
  67-column baseline, then record approval/status changes without duplicating
  or weakening its source, blank and conflict rules.
- Define PL.03 aggregation for multiple declarations per vessel, especially
  cargo names, dates, ports and agents that cannot be numerically summed.
- Define the audited PORT_STAFF or explicit-context PLATFORM_ADMIN manual-adjustment record and workflow for
  PL.02 call counts.
- Define the analytical dashboard projections separately from the official
  PL.01/PL.02/PL.03 exports.

Exit gate:

- **PASSED 2026-07-17:** entity ownership, field precedence, tenant scope,
  PL.02 adjustment and PL.03 aggregation are recorded in `DATA_PLATFORM_README.md`,
  `DATA_INDEX.md`, `DATA_FIELD_CATALOG.md`, `DATA_INHERITANCE_RULES.md` and
  `data_field_manifest.json`.
- **PASSED 2026-07-17:** the owner's instruction `Tiến hành sửa` authorizes the
  documented implementation plan in `REPORT_IMPLEMENTATION_PLAN_20260717.md`.

### T2 — Canonical foundation and provenance

Status: CLOSED — APPROVED LOCAL IMPLEMENTATION SCOPE 2026-07-17
Phase: BUILD

Actions:

- Normalize and connect Organization, Vessel, VesselOperatingProfile,
  CrewMember, Declaration/PortCall, CargoMovement, ImportJob/SourceRecord and
  AuditEvent.
- Add approved fields/relationships from T0, potentially including
  `arrival_berth`, `departure_berth`, `agent_or_operator_name` and an explicit
  passenger-call classification. Preserve the approved values in the event
  snapshot.
- Make Sổ theo dõi Salan a governed view/scope of canonical vessels rather than
  a second physical-vessel database.
- Preserve raw-source references and field-level conflict decisions.
- Add safe migrations, backup/rehearsal steps, idempotent import behavior and
  rollback evidence.

Exit gate:

- Migration rehearsal, integrity checks, tenant isolation, provenance and
  conflict-resolution tests pass.
- **PASSED 2026-07-17:** local DB backup and migration to `l11f0f000011`,
  canonical snapshot fields, append-only adjustment audit model and full test
  suite are recorded in the implementation handoff.

### T3 — Shared projections and inheritance between tabs

Status: CLOSED — APPROVED LOCAL IMPLEMENTATION SCOPE 2026-07-17
Phase: BUILD after T2

Actions:

- Expose role- and tenant-scoped API projections instead of duplicating data in
  tab-specific stores.
- Prefill Phiếu khai báo from canonical vessel and crew data, then freeze the
  approved event snapshot.
- Provide workflow controls to confirm ATA/ATD and any approved berth,
  agent/operator and passenger-call fields; ETA/ETD remain estimates rather
  than silently becoming actual values.
- Let Hồ sơ phương tiện and Sổ theo dõi Salan share vessel identity while
  retaining their different business scopes.
- Ensure crew selection is event-specific where required and does not create an
  unintended permanent vessel assignment.
- Record provenance and conflicts visibly in import/review workflows.

Exit gate:

- Cross-tab inheritance tests cover create, update, blank input, conflicting
  source, tenant boundary and approved-snapshot behavior.
- **PASSED 2026-07-17:** canonical vessel/crew/declaration projections,
  snapshot behavior, explicit-overwrite import rules and role/tenant controls
  are covered by the 95-test application suite.

### T4 — Report hardening and repeatable artifact assurance

Status: CLOSED — SPREADSHEET IMPLEMENTATION GATE PASS 2026-07-17
Phase: REVIEW after T3

Actions:

- Implement the decisions from T0 without changing the approved column
  meanings.
- Replace silent classification fallbacks with validation errors or an explicit
  review queue.
- Remove cross-class fallbacks such as actual passenger count into design
  capacity and destination port into departure berth.
- Apply the approved operating-date rule consistently to selected-period and
  year-to-date queries, including the no-activity blank rule.
- Test empty, one-row, template-row-count, expanded-row and mixed-cargo cases.
- Verify generated artifacts separately from source templates: values, column
  order, merges, widths, row heights, wrap, borders, alignment, signatures,
  print settings and visual renders.
- Keep a golden approved-event dataset distinct from static-vessel QA data.
- Include positive approved arrival/departure evidence with cargo, empty TEU,
  passengers, ATA/ATD, berth and agent/operator, plus explicit missing-versus-
  zero cases.

Exit gate:

- Automated mapping tests and Spreadsheet visual QA pass for all three files.
- All 67 canonical mappings are either PASS or covered by an approved,
  traceable exception; MAP-01 through MAP-05 are closed.
- Any remaining limitation is explicit; no `100% template compliant` claim is
  made without complete evidence.
- **PASSED 2026-07-17:** six-workbook regression plus focused PL.03 recheck
  close REG-01, APPX-01–04 and MAP-01–05 at implementation level.
- **LIMITATION:** live business data remains NOT PROVABLE because the
  operational database contains no approved declarations.

### T5 — Upstream CVF lesson extraction

Status: DEFERRED
Target repository: `D:\UNG DUNG AI\TOOL AI 2026\Controlled-Vibe-Framework-CVF`

Actions, in a separate CVF-core session only:

- Read the public core's `AGENTS.md`, `AGENT_HANDOFF.md` and roadmap conventions.
- Review the sanitized downstream proposal and choose an upstream tranche.
- Generalize the evidence-layer matrix, canonical inheritance contract, field
  catalog, provenance receipt and claim-strength gate.
- Use synthetic examples only; do not copy customer workbooks, database rows,
  contact details, secrets or downstream runtime artifacts.
- Run the CVF repository's required checks before proposing commit/publication.

Exit gate:

- Upstream artifacts are reviewed and accepted within the CVF core's own
  governance process. Downstream completion does not imply upstream acceptance.

## 5. Execution order

`T0 CLOSED → T1 CLOSED → T2 CLOSED → T3 CLOSED → T4 CLOSED → live-data acceptance → T5 DEFERRED`

No tranche may use the existence of this roadmap as implementation approval.
T2 and T3 are production-data/schema-impacting R2 work and require explicit
human review at the T1 gate.

## 6. Current hold point

The approved canonical-data and appendix implementation tranche is CLOSED for
the local implementation scope. T0 through T4 have passed their documented
business, design, migration, automated-test and Spreadsheet artifact gates.
The focused recheck reviewed seven artifact-tool renders: REG-01 is CLOSED,
positive PL.03 is PASS, the 47-Salan operational guardrail is PASS and the
overall Spreadsheet implementation gate is PASS.

The repository remains in REVIEW rather than claiming production/live-data
readiness. The operational database has 47 canonical Salan but no approved
declarations; therefore activity cells are correctly blank and live business
data remains NOT PROVABLE. The next downstream evidence step is to reconcile a
small approved operational sample against its declaration source using
`LIVE_DATA_VALIDATION_AND_POST_PILOT_RUNBOOK_20260717.md`. This live-data gate
is separate from the already closed implementation tranche. T5 remains deferred
and must be performed in a separate CVF-core session; no upstream change is
authorized here.

## 7. Separate historical-import workstream

The owner's new requirement to import old PL.01, PL.02 and PL.03 workbooks into
a historical reporting store is tracked separately in
`HISTORICAL_APPENDIX_IMPORT_AND_REPORTING_ROADMAP_20260717.md`. It does not
reopen the closed canonical appendix implementation tranche and must not create
synthetic declarations. The new H-series roadmap remains at INTAKE until real
sample workbooks are audited and its data/revision/overlap decisions are
approved.
