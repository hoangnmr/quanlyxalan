# Report Implementation Plan — 2026-07-17

Status: IMPLEMENTED AND REVIEWED — SPREADSHEET IMPLEMENTATION GATE PASS 2026-07-17.

1. Add declaration snapshots `departure_berth`, `agent_ptnd_name`, `is_passenger_call` and an append-only PL.02 adjustment model.
2. Expose the fields in API/import/form workflows with tenant and role controls.
3. Filter approved official reports by operating date, not creation date.
4. Implement full PL.01/PL.02 FORM blocks, monthly PL.02/YTD rules and deterministic PL.03 vessel aggregation.
5. Correct `TEUs`, `TEUs Rỗng`, `Quá cảnh`; repair PL.03 clipping without changing column order.
6. Add positive fixtures covering approval status, cross-month dates, blank versus zero, passenger call zero, shifted berth, agent snapshot and multiple declarations/cargo per vessel.
7. Run migration, backend, frontend and Spreadsheet visual regression gates before closing MAP/APPX implementation.
8. Preserve the canonical Salan row skeleton in PL.01/PL.03 and overlay only
   approved activity; verify the 47-row operational baseline separately from
   the synthetic positive fixture.

The Spreadsheet QA result `docs/CODEX_DESKTOP_SPREADSHEET_QA_RESULT_20260717.md`
is the baseline. The full regression and focused recheck close REG-01 and the
Spreadsheet implementation gate. APPX-01 through APPX-04 and MAP-01 through
MAP-05 are closed at implementation level. Live business data remains NOT
PROVABLE until approved operational declarations exist.
