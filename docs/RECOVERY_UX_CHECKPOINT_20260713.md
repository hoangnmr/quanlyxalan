# Recovery UX Checkpoint — 2026-07-13

## Tranche

- ID: RECOVERY-UX-T1
- Status: REMEDIATION PASS — Gate 5 closure pending full six-step wizard UAT
- Branch: `recovery/frontend-baseline-20260712`
- Baseline: `929a8c487c572b7bcad859e237b17da1d494a1db`
- Worktree: `Khai-bao-Cang-vu-recovery-ux`

## Controlled scope

This branch is isolated from both the active `main` worktree and the pristine
restore copy. Neither comparison source was edited.

Implemented in this checkpoint:

1. Restored a styled "Báo cáo hoạt động Cảng" block with tabs PL.01-PL.03.
2. Disabled analytics filters and download buttons with warning text: "Thống kê sản lượng chưa khả dụng".
3. Hid the external integration sync panel from Customer and Port Staff pages in app.js using style.display logic.
4. Converted the select multiple input in wizard step 4 to a friendly checkbox list.
5. Sized sidebar menu SVG icons to 16px to prevent layout breakage on mobile.

## Evidence

- CVF workspace enforcement doctor: PASS 17/17.
- `python -m pytest -q`: PASS 67/67.
- Migration `g06f0f000006` reached head on the isolated demo database; roles are
  `ADMIN`, `CUSTOMER`, `PORT_STAFF`, statuses are canonical, and no legacy
  declaration columns remain.
- Live API check: retired `QLC_APPROVE` returned HTTP 410; `PORT_APPROVE`
  released the previously stuck demo declaration id 8 to `APPROVED`.
- Backend contract test proves that the port employee can either approve the
  submitted declaration directly or request changes.
- Static checks contain no visible `Chờ CV`, `Chờ QLC`, `Chờ BP`, or
  `CV → QLC → BP` strings in `frontend/`.
- Live API reproduction before commit `5e74643`: Analytics returned 404 and
  customer access to integration returned 403. The frontend now avoids both
  invalid calls and regression remains PASS 67/67.
- **Browser/UAT evidence (2026-07-14):** Three remediation findings PASS. The
  wizard opens at Step 1, role-based integration visibility and mobile logout
  access are visually verified. Detailed evidence is recorded in
  `docs/BROWSER_EVIDENCE_RECOVERY_UX_20260714.md`.

## Not completed in this checkpoint

- Analytics restoration or implementation. The baseline frontend calls an
  analytics endpoint that is not present in the historical backend.
- Full six-step wizard UAT through Step 6, including validation/focus recovery,
  crew checklist and review/send evidence.

## Active risk and next governed move

- R2 remains active because the branch changes workflow-facing UX and is not
  yet integrated.
- Do not close Gate 5 or merge solely from the Step 1 screenshot. Complete the
  six-step browser journey and attach Step 4/Step 6 plus console/network proof.
- Analytics remains outside this tranche and is not a blocker for remediation
  verification, but it must not be described as implemented.
