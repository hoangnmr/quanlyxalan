# Work Order T1 — Identity, RBAC and Tenant Isolation

## Control block

- Work order: `WO-KBCV-T1-20260711`
- Status: CLOSED — Gate 1 reviewer evidence recorded in `docs/AGENT_HANDOFF.md`
- Depends on: T0 commit `6c8917d`
- CVF phase on assignment: BUILD
- Risk classification: R2
- Priority: P0 / security blocking
- Primary reference: `docs/EA_EVALUATION_ROADMAP.md`
- External APIs and production data: OUT OF SCOPE

## Objective

Make authenticated identity authoritative on the server, enforce role and
organization boundaries on every protected operation, and prevent a customer
or reviewer from reading or changing data outside their assigned scope.

T1 does not claim production security readiness. It establishes the mandatory
application authorization baseline for later hardening and deployment work.

## Preconditions

1. Run CVF doctor and require PASS before material work.
2. Confirm HEAD descends from T0 commit `6c8917d`.
3. Require a clean working tree or record and preserve pre-existing changes.
4. Run the T0 suite and require 32 tests PASS before changes.
5. Record human R2 approval in `docs/AGENT_HANDOFF.md` before BUILD.

## Authorized scope

- Identity/authentication and authorization code in `backend/`.
- User-to-organization model and migration artifacts required by T1.
- API query scoping and workflow authorization.
- Login/session handling changes required to remove client-authoritative roles.
- Focused frontend changes for login/logout/current-user and role-aware controls.
- Tests, ADR/API contract, README/security/deployment notes and handoff.

## Explicitly out of scope

- Real customer or production data migration.
- SSO/OIDC integration unless separately approved with an official contract.
- External registry or Maritime Authority API calls.
- UI redesign or frontend framework migration.
- PostgreSQL cutover, infrastructure deployment or production release.
- Deleting the local database to make tests pass.
- Editing CVF core or committing credentials/secrets.

## Target authorization model

### Roles

- `CUSTOMER`: manages data belonging to their organization and submits its
  declarations; cannot approve or issue permits.
- `CV`: reads submitted declarations in assigned operational scope; performs
  CV approval or requests changes.
- `QLC`: performs QLC approval only after CV approval; may request changes.
- `BP`: performs BP approval, issue and revoke according to state rules.
- `ADMIN`: manages users, organizations and controlled assignments; privileged
  operations must be audited. ADMIN does not silently impersonate workflow
  roles.

### Minimum permission matrix

| Capability | CUSTOMER | CV | QLC | BP | ADMIN |
|---|---:|---:|---:|---:|---:|
| Read/write own organization profile | Yes | No | No | No | Yes |
| Read/write own vessels and crew | Yes | Read | Read | Read | Yes |
| Create/edit own draft declaration | Yes | No | No | No | Yes |
| Submit own declaration | Yes | No | No | No | No |
| Read submitted operational queue | Own | Yes | Yes | Yes | Yes |
| CV approve/request changes | No | Yes | No | No | No |
| QLC approve/request changes | No | No | Yes | No | No |
| BP approve/issue/revoke | No | No | No | Yes | No |
| Manage users/role/org assignment | No | No | No | No | Yes |

Any broader cross-organization access requires an explicit operational-scope
model and human decision; do not infer global access from role name alone.

## Required tasks

### Task 1 — ADR and identity model

- Create ADR-002 covering bearer token/localStorage versus secure cookie/BFF
  session. Implement the approved local/pilot choice and document residual risk.
- Add user status and organization binding. Model reviewer operational scope
  explicitly if reviewers are not globally scoped.
- Define canonical role enum and reject unknown roles.
- Add `/api/auth/me` and logout/revocation behavior appropriate to the chosen
  session design.
- Never return password hashes, secret material or sensitive token claims.

### Task 2 — Secret and login hardening

- Remove the usable hard-coded JWT secret fallback outside explicit test/local
  mode; fail fast with a clear configuration error.
- Add `.env.example` with names only and non-secret guidance.
- Add configurable token/session lifetime and timezone-aware expiry handling.
- Add login rate limiting suitable for the current single-node pilot, password
  policy and generic authentication failure messages.
- Audit login success/failure without logging passwords or raw tokens.
- Remove any default admin password from automatic runtime bootstrap. Provide a
  documented one-time bootstrap mechanism requiring operator-supplied secret.

### Task 3 — Server-side authorization

- Implement reusable `require_roles(...)` and organization/scope enforcement.
- Apply authorization to every protected endpoint in `docs/API_CONTRACT.md`.
- Scope customer lists, searches, dashboard counts, suggestions, reports,
  attachments and prepared sync payloads by organization.
- Validate entity ownership on ID-based reads and writes; prevent IDOR.
- Derive workflow actor id/name/role from authenticated identity. Ignore or
  reject actor fields supplied by the client.
- Preserve the ordered workflow state machine in addition to role checks.
- Decide and document ADMIN break-glass behavior; default is deny for workflow
  approval actions.

### Task 4 — Data migration

- Add Alembic migration support sufficient for T1 identity/organization fields.
- Provide an upgrade path for existing local users without deleting data.
- Existing unbound non-admin users must be disabled or require explicit
  operator assignment; never grant a default organization silently.
- Back up the local database before any manual migration rehearsal. Do not
  commit the backup.

### Task 5 — Frontend contract

- Remove editable `actor_name` and `actor_role` as authority inputs.
- Load current user identity from `/api/auth/me`.
- Hide or disable actions the current role cannot perform, while retaining
  server-side enforcement as the security control.
- Implement explicit logout and expired-session handling.
- Ensure error messages distinguish unauthenticated (401) from unauthorized
  (403) without exposing sensitive details.

### Task 6 — Security tests

Build a matrix-driven suite covering at least:

- Every role against every protected capability.
- CUSTOMER A cannot list/read/update/delete CUSTOMER B organization, vessel,
  crew, declaration, attachment or report data.
- Sequential and guessed IDs do not bypass ownership checks.
- CUSTOMER cannot submit another organization's declaration.
- Client-supplied actor role/name cannot alter audit identity.
- CV, QLC and BP cannot perform another role's transition.
- Correct role still cannot skip workflow state.
- ADMIN cannot approve/issue unless explicit break-glass policy is approved.
- Disabled users and tokens for deleted/disabled users are rejected.
- Unknown roles and missing organization assignment fail closed.
- Login throttling, secret configuration and token expiry behavior.
- T0 functional regression suite remains green.

### Task 7 — Documentation and handoff

- Update API contract with role and organization scope for every endpoint.
- Document user bootstrap, assignment, login/logout and recovery procedures.
- Update threat model/security boundary and deployment configuration.
- Record exact migration and rollback rehearsal results.
- Update handoff with test counts, residual risks and next governed move.

## Acceptance criteria / Gate 1

1. All existing T0 tests PASS.
2. New authorization matrix and cross-tenant negative tests PASS.
3. Every protected API route has an explicit authentication, role and data-scope
   policy documented and tested.
4. CUSTOMER A cannot observe the existence or contents of CUSTOMER B records.
5. Workflow actor identity is server-derived and immutable in audit events.
6. CV -> QLC -> BP -> ISSUE requires both correct role and correct state.
7. Application fails safely when the signing secret is missing outside local
   test mode.
8. No default password, raw token, database or runtime attachment is committed.
9. Migration upgrade and bounded rollback rehearsal PASS on a copy of baseline
   data; original `data/` remains untouched.
10. `git diff --check` and CVF Doctor PASS.
11. Human security review approves the role matrix and residual risks.

## Verification evidence required

The delivery report must include:

- Baseline and final commit hashes.
- Exact test commands, total pass/fail/skip counts and matrix coverage.
- Route-to-policy coverage table.
- Migration upgrade/rollback commands and results.
- Secret-free configuration evidence.
- Files changed and why.
- Residual risks deferred to T2/T4.
- Final `git status --short`, `git diff --check` and Doctor result.

Do not use screenshots alone as security evidence. Do not print secrets, raw
tokens, password hashes or production/customer records.

## Stop and escalate conditions

Stop without destructive action when:

- Organization ownership or reviewer operational scope is ambiguous.
- Existing user records cannot be migrated without granting unintended access.
- SSO, email/SMS, external identity provider or production credentials become
  necessary.
- A requested permission conflicts with the approved matrix or workflow.
- Tests require real customer data.
- CVF doctor fails, human R2 approval is absent, or unrelated worktree changes
  conflict with implementation.

## Agent completion rule

Do not mark T1 CLOSED merely because authentication works. Closure requires
negative authorization evidence, tenant-isolation tests, migration evidence,
human security review and a committed clean tranche.
