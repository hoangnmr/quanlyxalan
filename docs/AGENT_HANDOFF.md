# Agent Handoff

## Tranche

`MVP-01` - customer vessel profile, declaration, Excel import, and reporting.

## Status

`REVIEW_COMPLETE_UNCOMMITTED`

## Implemented

- CVF-onboarded downstream project pinned to public core `a78b35c`.
- Separate static frontend and Python backend.
- SQLite schema for organizations, vessels, declarations, and audit events.
- Reusable vessel profile and declaration snapshot workflow.
- Deterministic container/TEU calculation matching the source workbook.
- Import mapping for the two provided XLSX templates.
- Appendix 1, 2, and 3 XLSX report endpoints.
- CVF Ops / Industrial responsive frontend with dark/light modes.

## Verification

- Python compile check: PASS.
- Backend unit tests: PASS (2/2).
- Runtime health, vessel create, declaration submit: PASS.
- TEU test: 7 containers -> 11 TEU; empty -> 3 TEU: PASS.
- Generated Appendix 3 opened by Microsoft Excel: PASS.
- Desktop and mobile headless-browser rendering: PASS after mobile topbar repair.
- CVF doctor: PASS (17/17).
- Workspace enforcement: PASS for all 11 governed projects.

## Active Risk

R2. The product handles customer and regulatory reporting data. Production use
still requires authentication, authorization, HTTPS, backup/restore, retention,
privacy review, and operator sign-off of the final Appendix visual mapping.

## Next Governed Move

Run final automated/CVF checks, then conduct operator UX acceptance using real
anonymized examples. Do not claim production or legal-approval readiness from
the MVP alone.
