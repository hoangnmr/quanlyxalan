# Report Implementation Plan — 2026-07-17

Status: BUILD AUTHORIZED by owner instruction `Tiến hành sửa`.

1. Add declaration snapshots `departure_berth`, `agent_ptnd_name`, `is_passenger_call` and an append-only PL.02 adjustment model.
2. Expose the fields in API/import/form workflows with tenant and role controls.
3. Filter approved official reports by operating date, not creation date.
4. Implement full PL.01/PL.02 FORM blocks, monthly PL.02/YTD rules and deterministic PL.03 vessel aggregation.
5. Correct `TEUs`, `TEUs Rỗng`, `Quá cảnh`; repair PL.03 clipping without changing column order.
6. Add positive fixtures covering approval status, cross-month dates, blank versus zero, passenger call zero, shifted berth, agent snapshot and multiple declarations/cargo per vessel.
7. Run migration, backend, frontend and Spreadsheet visual regression gates before closing MAP/APPX implementation.

The Spreadsheet QA result `docs/CODEX_DESKTOP_SPREADSHEET_QA_RESULT_20260717.md` is the baseline. APPX-04 is closed by exception; all other implementation items remain open until positive export evidence passes.
