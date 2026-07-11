# Work Order T5 — Product Professionalization

## Control block

- Work order: `WO-KBCV-T5-20260711`
- Status: IN PROGRESS — local/pilot scope started after T4 LOCAL_GATE_PASS
- Depends on: T4 CLOSED
- Risk: R1, elevated to R2 if authorization/workflow semantics change
- Priority: P2
- CVF phase on assignment: DESIGN then BUILD

## Objective

Improve operational usability, accessibility, responsiveness and performance
without weakening server-side authorization or changing legal/workflow meaning.

## Required tasks

1. Run task-based discovery with representative CUSTOMER, CV, QLC, BP and ADMIN
   users; define measurable success criteria and top failure points.
2. Create role-specific dashboards and queues showing only authorized actions,
   aging/SLA, certificate warnings and work requiring attention.
3. Add server-side pagination, sorting and filtering with stable query contracts,
   bounded page sizes and URL-preserved state.
4. Standardize form validation, field errors, loading, empty, offline/expired
   session and recovery states. Preserve safe browser draft recovery.
5. Improve workflow timeline, confirmation, change-request reason and permit
   issue/revoke safeguards.
6. Meet keyboard navigation, visible focus, dialog focus trapping, semantic
   labels, contrast and screen-reader requirements aligned to WCAG 2.2 AA.
7. Establish responsive regression coverage for agreed mobile/tablet/desktop
   viewports and reduced-motion behavior.
8. Add performance budgets for first load, interaction, table rendering and API
   response; test representative large datasets.
9. Create ADR-003 deciding continued modular Vanilla JS versus framework
   migration based on complexity, team ownership and lifecycle cost. A framework
   migration requires a separately approved implementation plan.
10. Add certificate expiry notifications and reminders with user-controlled,
    auditable delivery preferences; external messaging connectors remain out of
    scope unless separately approved.

## Gate 5 acceptance

1. Approved critical tasks meet success/time/error targets with representative
   users or an approved usability protocol.
2. Accessibility audit has no critical/serious unresolved findings.
3. Role UI never exposes an action the API forbids, and API remains authoritative.
4. Responsive and browser regression tests PASS.
5. Performance budgets PASS on the agreed reference dataset/device.
6. Full security/regression suite, `git diff --check` and CVF Doctor PASS.
7. Product owner and accessibility reviewer approve Gate 5.

## Stop and escalate

Stop if UX changes alter role authority, workflow/legal meaning, signed report
content or data retention. Do not adopt a new frontend framework without the ADR
and explicit scope approval.

## Delivery report

Include research protocol/results, before/after task metrics, accessibility and
performance reports, responsive matrix, ADR decision, residual issues and final
commit/Doctor evidence.

## Local checkpoint — 2026-07-11

- ADR-003 retains modular Vanilla JavaScript for the pilot; no framework
  migration is authorized or required.
- Added a keyboard skip link, route focus target, visible focus styling,
  screen-reader status announcements and an explicit dashboard busy state.
- Static frontend assertions cover the new semantic hooks.
- Declaration list uses an opt-in server-side pagination envelope with stable
  filters, an allowlisted sort contract and bounded `page_size` (1–100); old
  callers keep the compatible array response. Filter/page state is retained in
  the browser URL.
- Dashboard now exposes a server-calculated attention queue for the current
  role only, including count, oldest visible items and elapsed hours. It is an
  operational hint; workflow authorization remains server authoritative.
- Write forms now expose `aria-busy`, disable duplicate submit attempts and
  restore controls after success or error; API failures are announced as
  `role=alert`.
- Local automated evidence: `65 passed`; `git diff --check` PASS.
- Open before Gate 5: representative-user protocol/results, browser-assisted
  WCAG audit, responsive matrix and measured performance budget.
