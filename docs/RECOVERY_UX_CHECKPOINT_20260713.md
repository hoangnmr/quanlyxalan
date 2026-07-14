# Recovery UX Checkpoint — 2026-07-13

## Tranche

- ID: RECOVERY-UX-T1
- Status: REVIEWED — browser evidence collected, failed due to critical UI crashes and CSS leaks
- Branch: `recovery/frontend-baseline-20260712`
- Baseline: `929a8c487c572b7bcad859e237b17da1d494a1db`
- Worktree: `Khai-bao-Cang-vu-recovery-ux`

## Controlled scope

This branch is isolated from both the active `main` worktree and the pristine
restore copy. Neither comparison source was edited.

Implemented in this checkpoint:

1. Restored a styled, keyboard-addressable six-step wizard on the known-good
   frontend baseline.
2. Reordered declaration steps to vehicle, journey, cargo, crew, attachments,
   and review/send.
3. Replaced customer-facing submit terminology with “Xác nhận & gửi”.
4. Made reusable vessel-profile fields read-only after an existing vessel is
   selected. Administrators continue to maintain the reusable profile in the
   vehicle-record screen.
5. Removed visible CV/QLC/BP process stages from the application and preview.
6. Reduced the active workflow to customer confirmation followed by one port
   enterprise review: `PORT_APPROVE` or `REQUEST_CHANGES`.
7. Retired the legacy CV/QLC/BP/ISSUE/REVOKE API actions with HTTP 410 and
   added a controlled migration for legacy users, statuses, and columns.
8. Added inline wizard error summaries with focus recovery and replaced the
   native multi-select crew control with a keyboard-friendly checklist.
9. Prevented the Reports route from calling an unimplemented Analytics endpoint
   or an Admin-only integration endpoint for non-Admin users.
10. Limited the customer declaration entry point to `CUSTOMER` in the UI and
    removed remaining “Cảng vụ” wording from the active report navigation.

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
- **Browser/UAT evidence (2026-07-14):** Collected comprehensive screenshots and
  videos across three viewports (Desktop, Laptop, Mobile). Found a critical crash
  in the Customer Declaration Wizard and a serious security/CSS leak of the Admin Integration panel.
  Detailed evidence recorded in [BROWSER_EVIDENCE_RECOVERY_UX_20260714.md](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/BROWSER_EVIDENCE_RECOVERY_UX_20260714.md).

## Not completed in this checkpoint

- Analytics restoration or implementation. The baseline frontend calls an
  analytics endpoint that is not present in the historical backend.
- **RESOLVED (2026-07-14):** Live browser screenshot evidence. Multi-role multi-viewport visual testing has been completed. Gate 5 remains NOT READY (FAIL) due to critical visual findings.

## Active risk and next governed move

- Risk: R2 because workflow behavior, authorization, and data migration are involved.
- Next move: run this worktree locally, visually inspect desktop/mobile wizard,
  then either approve RECOVERY-UX-T1 or record layout corrections. Analytics
  must remain a separate tranche.

## Continuation handoff

Agent tiếp theo phải bắt đầu tại
`docs/SESSION_HANDOFF_RECOVERY_UX_20260713.md`. Trạng thái chi tiết từng finding,
phần đã sửa và điều kiện đang chờ nằm tại
`docs/UX_REEVALUATION_RECOVERY_BRANCH_20260713.md`.
