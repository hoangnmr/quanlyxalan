# Work Order T6 — External Authority Integrations

## Control block

- Work order: `WO-KBCV-T6-20260711`
- Status: MANUAL SCAFFOLD COMPLETE — activation deferred under explicit reopen conditions
- Depends on: T5 CLOSED plus official external prerequisites
- Risk: R2 minimum; R3 if production transmission or sensitive-data expansion
- Priority: P2
- CVF phase on assignment: INTAKE/DESIGN before BUILD
- Live evidence: mandatory for integration/release-quality governance claims

## Mandatory prerequisites

All items require named owners and written approval:

- Official API contract/version and sandbox endpoint.
- Credential issuance and rotation process.
- Data-sharing/privacy approval and allowed field list.
- Rate limits, availability expectations and support/escalation contacts.
- Idempotency, acknowledgement, rejection and reconciliation semantics.
- Test identities/data permitted in the sandbox.

Without these prerequisites, retain `PREPARED` preview-only behavior.

## Deferred activation / reopen condition

The manual-first, no-network adapter scaffold is complete. Reopen BUILD only
after all mandatory prerequisites above are supplied with named owners and the
required R2/R3 authorization is recorded. Until then, `PREPARED` is the final
allowed state and manual operation remains the supported path.

Manual-first adapter scaffolding may be built before these prerequisites. It
must make no network calls and must not block core workflows. See
`docs/EXTERNAL_ADAPTER_SPEC.md`.

## Objective

Implement a controlled adapter that sends only approved records to the Maritime
Authority or registry service, records immutable receipts and safely reconciles
timeouts, retries, duplicates and rejections.

## Required tasks after unblock

1. Create versioned adapter interfaces separated from domain logic. Restrict
   outbound destinations with an allowlist and TLS verification.
2. Store credentials in the approved vault/secret manager; never expose them in
   frontend, logs, evidence artifacts or repository.
3. Build an operator preview/approval gate showing payload version, record count,
   approved fields and checksum before transmission.
4. Use stable idempotency keys, bounded exponential backoff, timeout budgets,
   circuit breaking and dead-letter handling. Never retry permanent rejection
   blindly.
5. Persist request metadata, payload checksum, external correlation id, receipt,
   acknowledgement/rejection code and reconciliation state without storing
   secrets.
6. Enforce BP/ADMIN separation of duties as approved; sending authority must be
   server-side and audited.
7. Add reconciliation jobs and operator views for PREPARED, APPROVED, SENT,
   ACKNOWLEDGED, REJECTED, RETRY_PENDING and DEAD_LETTER states.
8. Add schema/version negotiation, backward compatibility policy and kill
   switch. Default connector state remains disabled.
9. Run contract and failure-mode tests against the official sandbox, including
   duplicate, timeout, partial failure, rate limit and invalid receipt cases.
10. Complete privacy/security threat review and operational incident runbook.

## Evidence rule

Mocks/fakes are allowed only for component logic and UI structure. They cannot
prove external connectivity, CVF governance behavior or production readiness.
Any such claim requires a real authorized sandbox/provider API call with a
secret-free request/response receipt under CVF policy.

## Gate 6 acceptance

1. Official sandbox contract tests and failure-mode tests PASS.
2. Idempotency and reconciliation prevent duplicate legal submissions.
3. Credentials and sensitive payloads are absent from logs/repository/evidence.
4. Human operator approval and kill switch are verified.
5. Privacy/security/authority owners approve the exact transmitted field set.
6. Full regression suite, `git diff --check` and CVF Doctor PASS.
7. Required live provider/API evidence is recorded for every release-quality or
   governance claim.
8. Formal human release approval is recorded before production enablement.

## Stop and escalate

Stop when official prerequisites are incomplete, sandbox behavior conflicts
with the contract, any credential appears in output, field scope expands, or
production sending would occur without R3/formal approval.

## Delivery report

Include contract/version, approved field inventory, sandbox evidence references,
failure-mode results, receipt/reconciliation proof, threat review, residual
risks and final commit/Doctor status. Never include raw secrets or customer data.
