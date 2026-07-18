# Canonical Data Platform

Status: T1 DESIGN CONTRACT — approved for BUILD by the owner's instruction `Tiến hành sửa` on 2026-07-17.

The operational database is the single system of record. Hồ sơ phương tiện, Phiếu khai báo, Sổ theo dõi Salan, Import Excel, dashboard and PL.01–PL.03 are projections of the same tenant-scoped entities; they are not separate data stores.

## Ownership

- `Vessel` owns current master facts.
- `Declaration` owns the approved port-call snapshot and workflow.
- Cargo facts remain attached to a declaration and are additive only through explicit report mappings.
- Report adjustments are append-only audit facts. They never rewrite declarations.
- Official appendix exports and the analytical dashboard are separate consumers.

PL.01 and PL.03 use the canonical Salan set as their row skeleton. Only
`APPROVED` declarations may fill activity columns; missing activity stays
blank. PL.02 is activity-only. Static master data may refresh static report
columns; approved activity, berth, agent, passenger classification and cargo
facts remain event snapshots.

## Product boundaries

- PL.01: canonical Salan rows with approved daily activity overlaid; it is not
  the internal register product even though both share the same master data.
- PL.02: one calendar month plus January-to-month cumulative values.
- PL.03: one canonical vessel per reporting period, including static-only
  vessels and aggregating eligible declarations where present.
- Sổ theo dõi Salan: internal management view over canonical vessels.
- Dashboard: analytical projection; it does not change official FORM semantics.
