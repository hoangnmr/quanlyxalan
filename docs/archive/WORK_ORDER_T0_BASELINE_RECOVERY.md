# Work Order T0 — Baseline Recovery and API Contract Restoration

## Control block

- Work order: `WO-KBCV-T0-20260711`
- Status: READY FOR ASSIGNMENT
- CVF phase on assignment: BUILD (only after human approval)
- Risk classification: R2
- Priority: P0 / blocking
- Target repository: `Quan-Ly-Xalan`
- Primary reference: `docs/EA_EVALUATION_ROADMAP.md`
- Production data/external API: OUT OF SCOPE
- CVF governance claim: OUT OF SCOPE; mocks may not be used for such claims

## Objective

Restore a coherent FastAPI baseline in which the documented local setup works,
the frontend and backend share one explicit API contract, critical MVP flows
work end-to-end, and automated tests pass from a fresh environment.

## Evidence the implementer must re-verify

1. Current `frontend/app.js` calls endpoints not implemented by the current
   221-line `backend/app.py`.
2. `scripts/run-dev.ps1` uses the old script-style server entry point.
3. `tests/test_backend.py` imports functions removed during FastAPI migration.
4. Current virtual environment lacks required runtime/test dependencies.
5. The working tree contains user/uncommitted changes. Preserve them and do not
   reset, checkout or overwrite unrelated work.

## Authorized scope

- `backend/`
- `frontend/` only for API-contract corrections required by this work order
- `tests/`
- `scripts/run-dev.ps1`
- dependency/config files required for local runtime and test
- relevant `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, handoff and
  ADR created by this work order

## Explicitly out of scope

- Production deployment or production data migration.
- Real Maritime Authority or registry API calls.
- UI redesign, React/Vue migration, animations or visual polish.
- Final RBAC/tenant-isolation implementation; preserve authentication boundaries
  and record gaps for T1.
- Deleting or transforming `data/cang_vu.db` or user uploads.
- Editing the CVF core repository.
- Adding default credentials, secrets or API keys.

## Required tasks

### Task 1 — Preserve and inventory

- Run CVF doctor and record PASS before material work.
- Capture `git status --short` and identify pre-existing changes.
- Compare working tree with commit `29ef124` read-only.
- Produce `docs/API_CONTRACT.md` listing method, path, auth requirement,
  request/response model, frontend caller and implementation status.
- Select FastAPI as target architecture; port behavior deliberately rather than
  reverting the whole working tree.

### Task 2 — Runtime baseline

- Make `backend` importable as a package.
- Update local launcher to run `uvicorn backend.app:app` from project root.
- Pin compatible Python dependencies and include test dependencies separately.
- Document supported Python version and fresh-environment commands.
- Add startup configuration validation without introducing production secrets.

### Task 3 — Restore API feature parity

At minimum reconcile all calls currently present in `frontend/app.js`:

- auth login and health
- catalogs, dashboard, organizations
- vessels CRUD/list and local registry-date verification
- crew CRUD/list
- declarations list/create/update/submit
- declaration events and ordered workflow transition
- suggestions
- attachment upload with existing signature/size rules
- vessel/declaration Excel import
- Appendix report exports
- integration status and prepare-only sync jobs

For any feature intentionally deferred, remove or disable its UI entry and
document the decision in the API contract. Do not leave silent 404 behavior.

### Task 4 — Validation and transaction safety

- Use Pydantic request models for restored write endpoints.
- Restore required-field, numeric, ETA/ETD and workflow-order validation.
- Use one transaction boundary per write operation and rollback on error.
- Return consistent JSON error shape for validation, conflict and not-found.
- Keep submitted declaration snapshots protected from ordinary edits.

### Task 5 — Rebuild automated tests

- Replace tests tied to the stdlib backend with FastAPI/SQLAlchemy tests.
- Isolate test database and file storage in temporary directories.
- Cover at least:
  - health and static frontend;
  - authentication required on protected routes;
  - vessel and crew create/read/update;
  - declaration draft and submit;
  - TEU calculations;
  - ordered CV -> QLC -> BP -> ISSUE transition;
  - skipped workflow stage rejection;
  - submitted-record edit protection;
  - attachment signature/size rejection;
  - Excel import and XLSX report package generation;
  - every frontend endpoint has a registered backend route or declared disabled
    state.

### Task 6 — Documentation and handoff

- Update README, architecture and deployment commands to match actual code.
- Create ADR-001 recording migration/feature-parity decisions.
- Update `docs/AGENT_HANDOFF.md` with exact tests run, results, open risks and
  next governed move.
- Do not mark CLOSED until all acceptance criteria are satisfied.

## Acceptance criteria

1. From a fresh environment, documented install command succeeds.
2. Documented test command returns exit code 0.
3. Documented start command serves `/api/health` and `/` successfully.
4. Critical flow passes: login -> create vessel/crew -> draft declaration ->
   submit -> ordered approvals -> issue -> report export.
5. No unexpected frontend API request returns 404.
6. Test database/storage cannot affect `data/`.
7. No hard-coded production secret or default admin password is added.
8. Existing user changes outside work-order scope remain intact.
9. `git diff --check` passes and changed files are reviewed.
10. CVF doctor passes at handoff.

## Verification commands

The implementer may adjust commands only if the final documentation is updated:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080
```

Also run:

```powershell
git diff --check
powershell -ExecutionPolicy Bypass -File `
  "<cvf-core>\scripts\check_cvf_workspace_agent_enforcement.ps1" `
  -ProjectPath "<project-root>"
```

## Required delivery report

The assigned agent must report:

- Files changed and why.
- API contract coverage before/after.
- Exact test commands and pass/fail counts.
- Any behavior intentionally deferred.
- Security gaps left for T1.
- Database compatibility or migration observations.
- Git status and commit hash, if the human owner authorizes committing.

## Stop and escalate conditions

Stop without destructive action if:

- Existing uncommitted changes conflict with the selected implementation.
- Restoring feature parity requires changing or deleting real data.
- A choice would materially alter the workflow or signed report mapping.
- External credentials/API access is required.
- CVF doctor fails or phase/risk approval is missing.

