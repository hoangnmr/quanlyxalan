# Maritime Report Mapping Specification

- Spec id: `KBCV-REPORT-MAP-1.1`
- Status: IMPLEMENTED; SPREADSHEET IMPLEMENTATION GATE PASS
- Initial approval date: 2026-07-11
- Owner reconfirmation: 2026-07-17
- Reporting unit: **Cảng Tân Thuận**
- Port label: **Cảng Sài Gòn-Cảng Tân Thuận**
- Source templates: `templates/Phụ lục 1.docx`, `templates/Phụ lục 2.docx`,
  `templates/Phụ lục 3.xlsx`

## Product and reporting-period boundaries

- PL.01 is the daily Port-company report driven only by approved customer
  declarations.
- PL.02 produces one official form for one selected calendar month. Its
  `Thực hiện tháng báo cáo` columns contain that month only; its
  `Lũy kế đến tháng báo cáo` columns contain January 1 through the end of the
  selected month.
- PL.03 is an official Port-company appendix for the selected reporting period
  and aggregates approved customer declarations by canonical vessel.
- Sổ theo dõi Salan and its week/month/year statistics are a separate internal
  Port-management product for staff and leadership. Static register rows do
  not become PL.01/PL.02/PL.03 activity without an eligible declaration.
- The web application requires a separate analytical reporting dashboard.
  Flexible week/month/year or date-range analytics do not change the official
  monthly structure or wording of PL.02.

## Eligible declarations

- PL.01 and PL.03 row population is the canonical Salan master set plus any
  unmatched eligible call; only declarations in `APPROVED` workflow state may
  populate activity columns. Static-only rows keep activity blank.
- PL.02 remains activity-only and includes only `APPROVED` declarations.
- Exclude `DRAFT`, pending review states, `CHANGES_REQUESTED`, cancelled and
  `REVOKED` declarations.
- Report queries remain tenant-scoped for CUSTOMER users.

## Arrival and departure times

- Arrival uses `actual_arrival_at` (ATA) when present; otherwise uses `eta`.
- Departure uses `actual_departure_at` (ATD) when present; otherwise uses `etd`.
- ETA, ETD, ATA and ATD remain distinct source fields for traceability.
- `declaration_date` is the form creation date and must not determine the
  operating reporting month.
- PL.02 `Lượt tàu` is counted by operating arrival (`ATA`, fallback `ETA`). A
  departure in a later month does not create another call by default.
- PORT_STAFF and ADMIN may apply a controlled manual reporting adjustment. The
  adjustment must record report month, metric, before/after value, reason,
  actor and timestamp; it must never rewrite the source declaration silently.

## Official form fidelity

- Appendix 1 reproduces the complete official form, including its title/date,
  reporting-company information, note block and 16-column table.
- Appendix 2 reproduces the complete official monthly form, including its
  title, `Tháng` field and 16-column monthly/cumulative table.
- Appendix 2 must retain the exact meanings `Thực hiện tháng báo cáo` and
  `Lũy kế đến tháng báo cáo`; `kỳ báo cáo` is not an approved substitute.
- Appendix 3 preserves the 35-column form, merged headers and formatting. The
  owner-approved export exception does not require the preparer/authority
  signature block.
- Standardize the Appendix 3 labels to `TEUs`, `TEUs Rỗng` and `Quá cảnh` in
  the approved template/export revision.

## Vessel register inheritance

- A report row remains driven by an approved declaration/trip.
- When its registration number matches a vessel in Hồ sơ phương tiện / Sổ theo
  dõi Salan, current vessel name, type, class, dimensions, capacities,
  certificate expiry and tracked master contact take priority over the older
  declaration snapshot.
- Multiple operating-area profiles remain separate source records. Exported
  cells retain all corresponding deadweight and cargo-capacity values in their
  stored order instead of selecting or averaging one profile.
- Static register records alone do not fabricate a vessel call, cargo movement
  or passenger movement in an activity report.

## Canonical position, passenger and agent rules

- PL.01/H is static design passenger capacity. It must never fall back to the
  actual `declarations.passenger_count`.
- PL.01/O is actual crew/passenger count for the eligible declaration.
- PL.01/I is the approved arrival/working port or berth. PL.01/K is the approved
  departure berth and needs a distinct event snapshot because a vessel may
  shift berth within the same port.
- `destination_port` is the next destination and must not populate PL.01/K.
- PL.03/AE is `Cảng đến (Cảng làm hàng)` / working port. PL.03/AF is the next
  destination port.
- PL.03/AI keeps the official label `Đại lý PTND` and uses the explicit value
  declared by the customer for the approved call. Do not infer it from current
  `company_name` after approval.
- A passenger vessel that berths counts as a passenger call even when actual
  passenger count is zero. `passenger_count > 0` is not a valid call classifier.
- No eligible activity, or an eligible call with no applicable cargo/passenger
  measure, is rendered as blank rather than a synthetic numeric zero. A light
  gray no-data presentation may be designed without changing value semantics.

## PL.03 vessel aggregation and PL.02 totals

- PL.03 emits one row per canonical Salan/vessel for the reporting output, not
  one row per cargo item.
- All eligible approved customer declarations and cargo items contributing to
  that vessel are preserved as source facts and aggregated into the applicable
  cargo-category columns.
- Non-additive PL.03 fields such as cargo names, dates, ports and agents retain
  distinct nonblank values in chronological order and join them with a line
  break in the same cell. Source declarations remain the drill-down and
  reconciliation records.
- Appendix 2 totals both eligible load and unload/import and export activity,
  grouped by the approved cargo categories, without double counting.
- Appendix 2 provides selected-month totals and January-through-selected-month
  cumulative totals.
- Container conversion remains 20 feet = 1 TEU and 40 feet = 2 TEU.

## Import policy

- Imports use partial acceptance.
- Every rejected row returns its source row number and a safe validation error.
- Accepted rows commit independently through savepoints.
- Template/mapping version and source checksum must be recorded; repeat imports
  must be idempotent.

## Administrative editing

- ADMIN may edit data across organizations.
- Server-side validation, optimistic version checks and audit logging remain
  mandatory.
- Submitted/approved declaration changes must use the governed correction flow;
  ADMIN authority does not silently bypass snapshot or workflow rules.

## Approval boundary

This approval covers business meaning, product boundaries and selection rules.
It authorizes DESIGN only. It does not authorize schema/code/template changes,
external transmission, legal acceptance by the Maritime Authority or
production deployment. BUILD requires an approved T1 data contract and
acceptance-test plan.
