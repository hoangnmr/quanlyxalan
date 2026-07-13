# Recovery UX Checkpoint — 2026-07-13

## Tranche

- ID: RECOVERY-UX-T1
- Status: IN_PROGRESS — awaiting human visual review
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
6. Added the `PORT_APPROVE` transition from `PENDING_REVIEW` directly to
   `APPROVED`, while preserving legacy transitions temporarily for historical
   audit/data compatibility.

## Evidence

- CVF workspace enforcement doctor: PASS 17/17.
- `python -m pytest -q`: PASS 68/68.
- Backend contract test proves that the port employee can either approve the
  submitted declaration directly or request changes.
- Static checks contain no visible `Chờ CV`, `Chờ QLC`, `Chờ BP`, or
  `CV → QLC → BP` strings in `frontend/`.

## Not completed in this checkpoint

- Analytics restoration or implementation. The baseline frontend calls an
  analytics endpoint that is not present in the historical backend.
- Live browser screenshot evidence. No in-app browser window was available in
  this session; human visual review remains mandatory before closure.
- Removal/migration of legacy role and workflow codes from persisted data.
  They are retained below the UI boundary to avoid an uncontrolled migration.

## Active risk and next governed move

- Risk: R2 because workflow behavior and authorization are involved.
- Next move: run this worktree locally, visually inspect desktop/mobile wizard,
  then either approve RECOVERY-UX-T1 or record layout corrections. Analytics
  must remain a separate tranche.
