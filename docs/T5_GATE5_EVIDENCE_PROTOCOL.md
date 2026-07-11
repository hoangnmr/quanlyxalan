# T5 Gate 5 Evidence Protocol — Local/Pilot

**Status:** READY FOR EXECUTION (no findings or user-acceptance results claimed)

## Reference conditions

- Test current `main` on the local pilot URL with a seeded representative data
  set. Record browser/version, viewport, device class and database row counts.
- Test at 375×667, 768×1024 and 1440×900 CSS pixels; repeat the keyboard pass
  with reduced motion enabled.
- Use one representative account per role: CUSTOMER, CV, QLC, BP and ADMIN.
  The API is the authority if the visible UI and API response ever disagree.

## Task study

| Role | Critical task | Success measure | Target |
|---|---|---|---|
| CUSTOMER | Create, save then submit a declaration with one attachment | Completed without assistance; required validation understood | ≥90% success, ≤8 min |
| CV | Locate assigned review queue and request a correction with a reason | Correct declaration and trace created | ≥90%, ≤3 min |
| QLC | Locate and approve a pending QLC declaration | No attempts on prohibited status | ≥90%, ≤2 min |
| BP | Issue a permit after all approvals | Permit recorded and timeline updated | ≥90%, ≤2 min |
| ADMIN | Filter declarations, inspect attention queue and edit approved data | Correct scope; audit/version protection remains intact | ≥90%, ≤4 min |

Record completion, elapsed time, errors, assist level, task comments and any
workflow misunderstanding. Do not count a workaround as a success.

## Accessibility / responsive checklist

1. Keyboard-only: skip link is first focusable item; focus is visible; route
   change lands on main content; every dialog can open, close and submit.
2. Screen reader: page context, toast error, busy state, labels and form
   validation are announced; decorative assets do not create noise.
3. Visual: normal/hover/focus/error states are distinguishable without color
   alone; text remains readable at 200% zoom; reduced motion removes animation.
4. Responsive: no horizontal page overflow at reference viewports; tables
   retain header meaning through mobile `data-label` rendering; dialogs remain
   operable at 375px width.
5. Authority: use browser devtools or direct HTTP calls to attempt an action
   hidden for the current role; API must return its expected denial.

Classify each issue as critical, serious, moderate or minor. Gate 5 permits no
unresolved critical or serious accessibility issue.

## Performance measurement

Use a warm local run with browser cache state recorded. Capture three samples
and use the median for each metric.

| Scenario | Local pilot target | Measure |
|---|---:|---|
| Initial dashboard API | ≤500 ms | browser network duration |
| Filtered declaration page (25 rows) | ≤750 ms | browser network duration |
| Render a 25-row declaration list | ≤250 ms after API response | performance mark / devtools |
| Save draft acknowledgement | ≤1 s | click to visible success state |
| Page payload | document + JS + CSS ≤750 KB before user data | network transfer |

If a target fails, retain the trace, input size and database size, then create a
remediation work item. These are pilot targets only; production targets need a
named hosting/device baseline.

## Required evidence for Gate 5 closure

- Completed task-study sheets and aggregate metrics.
- Browser/assistive-technology accessibility report and issue disposition.
- Responsive viewport matrix and performance traces.
- Security/regression result, `git diff --check`, CVF Doctor result.
- Product owner and accessibility reviewer approval.
