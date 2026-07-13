# Work Order T5 UX Remediation — Claude

## Control block

- Work order: `WO-KBCV-T5-UXR-20260713`
- Assignee: Claude
- Status: LOCAL IMPLEMENTATION COMPLETE — GATE 5 EVIDENCE PENDING
- Parent: `WO-KBCV-T5-20260711`
- Phase: REVIEW
- Risk: R1; escalate to R2 before changing role authority, workflow semantics,
  legal form mapping or report meaning
- Priority: P0 accessibility/error recovery, then P1 interaction optimization

## Objective

Improve the real user experience of declaration and review tasks using the
evidence in `docs/UX_EVALUATION_RESPONSE_20260713.md`, while preserving API
contracts, RBAC, tenant isolation, audit behavior and legal/report mappings.

Feature completeness alone is not acceptance. Delivery must show that the UI is
keyboard-operable, understandable, recoverable after error and efficient for
each role.

## Baseline already implemented before assignment

The following changes are present and must be verified, not silently replaced:

1. Wizard steps render native buttons with accessible names, `aria-current` and
   disabled future steps.
2. Local draft status explicitly says the draft is stored on this device and is
   not yet saved to the system; the local save time is displayed.
3. Static regression tests are in `tests/test_frontend_ux.py`.
4. Local baseline: `69 passed`; JavaScript syntax check and `git diff --check`
   PASS before this work order was issued.

## Required tasks

### T1 — Verify the P0 baseline in a real browser

- Test wizard navigation using Tab, Shift+Tab, Enter and Space.
- Verify visible focus, current-step announcement, disabled future steps and
  navigation back to completed steps.
- Verify local draft wording on first open, after input, after reload and after
  a successful server-side draft save.
- Test at 375×667, 768×1024 and 1440×900, plus 200% zoom.
- Record browser/version, viewport, expected/actual and screenshot or trace.

### T2 — Form error recovery

- Add inline field errors and a step-level error summary for the declaration
  wizard.
- Focus the first invalid field when validation fails.
- Keep the error visible until corrected; do not rely only on a disappearing
  toast or native validation bubble.
- Preserve values and local draft state after 403, 409, 422 and transient
  request failures.
- Announce the summary and field errors to screen readers without duplicate
  noise.

Acceptance:

- invalid data on every wizard step is discoverable using keyboard and screen
  reader;
- correcting a field clears only its own error;
- no data is lost after API error;
- negative and regression tests PASS.

### T3 — Crew selection interaction

- Replace native `<select multiple>` with a keyboard/touch-friendly checklist
  or searchable picker.
- Show full name, crew role, certificate status and identify the captain.
- Preserve selected crew when moving between wizard steps or restoring a local
  draft.
- Do not alter crew authorization, ownership or API payload meaning.

Acceptance:

- mouse, touch and keyboard paths work;
- selected count and captain are understandable without opening another page;
- mobile layout has no horizontal overflow;
- API still receives the existing `crew_ids` contract.

### T4 — Role-focused dashboard hierarchy

- CUSTOMER: prioritize drafts, change requests and creation/resume actions.
- CV/QLC/BP: prioritize the current role's actionable queue and aging.
- ADMIN: separate operational/backup information from normal declaration work.
- Move personal reminder settings out of the primary task hierarchy or visually
  demote them.
- Do not infer permission from UI visibility; the API remains authoritative.

Acceptance:

- each role sees its next work without manually constructing filters;
- attention queue contains only statuses actionable/visible to that role;
- direct forbidden requests still receive the expected API denial;
- role-specific screenshots and HTTP evidence are attached.

### T5 — Terminology and contextual help

- Standardize user-facing Vietnamese: use “Nhập Excel”, “Sao lưu”, “Danh sách
  thuyền viên” and plain-language status descriptions where appropriate.
- Do not expose internal names such as `payload`, `crew_ids` or
  `workflow_status` in user-visible errors.
- Add short contextual explanations for local draft storage, locked submitted
  records and unavailable actions.

### T6 — Complete missing evidence

Execute the test list in sections 8.1–8.5 of
`docs/UX_EVALUATION_RESPONSE_20260713.md`, including:

- representative task study for CUSTOMER, CV, QLC, BP and ADMIN;
- keyboard and screen-reader pass;
- responsive matrix and 200% zoom;
- actual 25-row browser render trace;
- three click-to-visible draft-save samples;
- cold/warm cache and total transferred asset size;
- expanded RBAC/tenant/role UX matrix.

## Explicitly deferred / requires owner decision

- Changing the owner-approved order A/B/C-D/E/attachments/F again, or changing
  the legal meaning of any section.
- Changing role permissions or workflow transitions.
- Changing signed report mappings or external authority behavior.
- Claiming production performance from local SQLite measurements.
- Closing Gate 5 without representative-user and accessibility evidence.

Stop and request approval before any deferred item is changed.

## Required tests and gates

1. `node --check frontend/app.js` PASS.
2. Full `pytest -q` PASS.
3. New automated coverage for error recovery, crew selection and role UI.
4. `git diff --check` PASS.
5. CVF Workspace Doctor PASS 17/17.
6. Browser evidence names the role, viewport, dataset and expected/actual.
7. No secrets, runtime database, attachments or raw tokens committed.

## Worktree boundary

The worktree may contain owner changes unrelated to this work order. Preserve
them and commit only files intentionally changed for `WO-KBCV-T5-UXR-20260713`.
Do not add `seed.py`, `scripts/seed.py` or unrelated changes in
`tests/test_backend.py` unless the owner explicitly brings them into scope.

## Delivery report

Update `docs/UX_EVALUATION_RESPONSE_20260713.md` with before/after evidence and
mark each finding as VERIFIED_FIXED, OPEN or BLOCKED. Update
`docs/AGENT_HANDOFF.md` with completed work, remaining evidence, risk and next
governed move. Do not declare Gate 5 closed while any serious accessibility
finding or required evidence remains open.
