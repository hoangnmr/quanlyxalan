# Recovery UX Checkpoint — 2026-07-13

## Tranche

- ID: RECOVERY-UX-T1
- Status: IN_PROGRESS — implementation complete, awaiting human visual review
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

## Not completed in this checkpoint

- Analytics restoration or implementation. The baseline frontend calls an
  analytics endpoint that is not present in the historical backend.
- Live browser screenshot evidence. No in-app browser window was available in
  this session; human visual review remains mandatory before closure.

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
