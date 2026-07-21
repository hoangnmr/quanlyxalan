# CVF Upstream Use Case — Canonical Data Inheritance and Governed Appendix Audit

Status: PROPOSED FOR UPSTREAM REVIEW
Date: 2026-07-16
Downstream project: Quan-Ly-Xalan-recovery-ux
Proposed public-core target: `D:\UNG DUNG AI\TOOL AI 2026\Controlled-Vibe-Framework-CVF`
Target remote: `https://github.com/Blackbird081/Controlled-Vibe-Framework-CVF.git`

## Purpose

Capture a reusable CVF case study from a downstream port-operations project:

1. audit mixed Word/Excel regulatory templates;
2. verify generated workbooks separately from source templates;
3. distinguish master data, event data, and aggregates;
4. define a canonical shared-data layer used by multiple UI tabs;
5. retain field-level provenance and explicit evidence boundaries;
6. publish an index/README control plane without confusing it with the
   operational database.

This artifact is an upstream handoff proposal. It does not modify the CVF core,
claim production readiness, or copy operational/customer data into CVF.

## Downstream Trigger

The application contains three official report structures:

- PL.01: 16-column vessel/activity plan;
- PL.02: 16-column current-period and cumulative activity summary;
- PL.03: 35-column detailed port-call report using the original XLSX template.

The local database contained vessel-register records but no approved
declarations. Direct web exports were therefore correctly empty, while a
separate QA-only workbook populated static vessel fields to test column mapping
and formatting. This exposed a recurring governance risk: a visually populated
artifact can be mistaken for an official activity report even when it contains
no qualifying event data.

The approved downstream rule is:

- an official report row is driven by an approved declaration/trip;
- current vessel-register fields may enrich that row;
- static vessel records alone must not fabricate calls, cargo movements,
  passengers, or production totals.

## Evidence Layers Discovered

A single “spreadsheet audit passed” statement was not sufficient. The work
separated evidence into four layers:

| Layer | Question | Required evidence |
|---|---|---|
| Template contract | What does the issued form require? | Full DOCX/XLSX structure, headers, merges, widths, wrapping, borders, and page geometry |
| Generator contract | Does code map fields to the intended columns? | Field-by-field mapping against generator and row-building code |
| Dynamic export | What does the running exporter actually produce? | Real endpoint/function output with known approved data and boundary cases |
| Visual verification | Is the delivered workbook legible and stable? | Render of every sheet plus targeted inspection of headers and data rows |

Each layer must state which tool/runtime was used and what was not verified.
Static source review must not be promoted to dynamic or visual proof.

## Tool-Capability Lesson

The spreadsheet workflow required `load_workspace_dependencies` and
`@oai/artifact-tool`. The skill could be installed and enabled while the
dependency loader was still absent from a particular session.

Reusable CVF rule proposal:

1. declare the exact required capability before the audit;
2. confirm the loader/runtime is callable in the active session;
3. stop when the mandated capability is missing if fallback was prohibited;
4. never describe a fallback audit as proof produced by the mandated skill;
5. record the runtime/bundle version in the evidence artifact.

This is a capability-evidence gate, not merely a package-installed check.

## Canonical Data Model Lesson

Multiple tabs should not own independent copies of the same business data.
They should project from a canonical data plane:

```text
Excel / API / UI sources
          |
          v
Raw source receipt + import job + checksum
          |
          v
Normalize / validate / deduplicate / resolve conflicts
          |
          v
Canonical operational database
          |
          v
Domain APIs and governed projections
          |
          v
Vessel register / Salan tracking / declarations / crew / reports
```

Recommended entity classes:

- `Organization`: owner/operator identity;
- `Vessel`: canonical vessel master;
- `VesselOperatingProfile`: ordered operating-area capacities;
- `CrewMember`: canonical crew master;
- `Declaration` or `PortCall`: event/workflow record;
- `CargoMovement`: normalized cargo activity;
- `ImportJob` and `SourceRecord`: source checksum, row, mapping version, and
  acceptance result;
- `AuditEvent`: actor, timestamp, before/after state, and correction reason.

## Inheritance Contract

Every inherited field should define:

- canonical entity and field;
- source priority;
- whether blank input may overwrite a non-blank canonical value;
- current-value versus approved-event snapshot behavior;
- tenant/organization boundary;
- validation and conflict rule;
- provenance metadata;
- downstream tabs and reports that consume it.

Baseline inheritance rules:

1. Hồ sơ phương tiện is the vessel master.
2. Sổ theo dõi Salan is a governed view/subset of the vessel master, not a
   second independent vessel table.
3. Phiếu khai báo pre-fills from the vessel and crew masters, then records an
   auditable snapshot at submission/approval.
4. Reports require approved event data; they may enrich static fields from the
   current master only where the approved mapping contract permits it.
5. Empty values from a lower-priority source do not erase validated canonical
   values.
6. Derived totals are calculated from normalized events, never from design
   capacity or template placeholders.

## Index/README Control Plane

The CVF-like index is a discovery and governance surface, not the operational
data store. A downstream implementation should provide:

- `DATA_PLATFORM_README.md`: purpose, lifecycle, and ownership;
- `DATA_INDEX.md`: entity/table/API/tab map;
- `DATA_FIELD_CATALOG.md`: field types, validation, owner, sensitivity, and
  consumers;
- `DATA_INHERITANCE_RULES.md`: priority, snapshot, and conflict policy;
- a machine-readable catalog/manifest consumed by tests and agent workflows.

The database remains the system of record. The index tells humans and agents
how to find, interpret, and safely change that record.

## Proposed CVF Upstream Pattern

CVF could generalize this case into a reusable pattern containing:

1. `CANONICAL_DATA_INHERITANCE_USE_CASE.md` — narrative and decision model;
2. `ARTIFACT_AUDIT_EVIDENCE_MATRIX.md` — template/code/dynamic/visual gates;
3. `DATA_FIELD_CATALOG_TEMPLATE.md` — field-level source and inheritance map;
4. `DATA_PROVENANCE_RECEIPT_TEMPLATE.md` — import/source/mapping/checksum
   receipt;
5. a machine-readable data-contract schema;
6. release-gate checks that reject claims stronger than the available evidence.

## Suggested CVF Acceptance Criteria

- A downstream project can distinguish master, event, aggregate, and derived
  data in a machine-readable contract.
- Every report column maps to a canonical field or explicit derivation.
- Every inherited field declares current-value/snapshot behavior.
- Imports retain source checksum, mapping version, and per-row result.
- Duplicate and conflict rules are deterministic and auditable.
- Static-only data cannot produce official activity metrics.
- Template, generator, dynamic-export, and render evidence are reported
  separately.
- Missing required tools cause an explicit blocked result rather than silent
  fallback.
- No secrets, customer payloads, or raw provider credentials are copied into
  upstream CVF artifacts.

## Downstream References

- `docs/REPORT_MAPPING_SPEC.md`
- `docs/REPORT_GOLDEN_DATASET.md`
- `docs/DEMO_DATA_POLICY.md`
- `docs/APPENDIX_TEMPLATE_AUDIT_20260716.md`
- `backend/xlsx_io.py`
- `backend/app.py`

## Transfer Boundary

Because this project is governed as an isolated downstream sibling, upstream
application must occur in a separate CVF-core session:

1. open the public-core repository as the active workspace;
2. read its `AGENTS.md` and `AGENT_HANDOFF.md`;
3. verify branch, remote, and worktree state;
4. review this proposal for public-safe content;
5. choose the appropriate CVF roadmap/tranche;
6. implement, test, commit, and publish from the CVF repository only after the
   required review/approval.

Do not copy downstream databases, generated customer workbooks, credentials,
or raw operational records into the CVF core.
