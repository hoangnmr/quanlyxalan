# Work Order T4 — Operability and Production Foundation

## Control block

- Work order: `WO-KBCV-T4-20260711`
- Status: LOCAL_GATE_PASS — production Gate 4 remains blocked on infrastructure
- Depends on: T3 CLOSED
- Risk: R2 / Priority: P1
- CVF phase on assignment: BUILD then REVIEW
- Production release: requires separate human approval

## Objective

Provide reproducible deployment, observability, backup/restore, security
hardening and CI gates sufficient for a controlled staging environment and a
future production release decision.

Approved local-first decisions are recorded in
`docs/T4_LOCAL_OPERATING_PROFILE.md`. Hosting/domain/staging are deferred, so
the initial implementation may only claim `LOCAL_GATE_PASS`.

## Required tasks

1. Create a pinned multi-stage container build, non-root runtime, read-only root
   filesystem where practical, health checks and explicit persistent volumes.
2. Define environment configuration and secret injection. Fail fast for missing
   required values; never bake secrets into image, compose files or logs.
3. Add CI gates for formatting, lint, type check, unit/integration/contract
   tests, migration test, dependency audit, SAST, secret scan and container scan.
4. Add structured JSON logs with request/correlation id, authoritative actor,
   route, status, latency and safe error classification. Redact PII/secrets.
5. Add liveness/readiness endpoints that distinguish process health, database
   readiness and migration compatibility.
6. Define metrics and alerts for error rate, latency, auth failures, job backlog,
   database capacity, backup age and certificate expiry.
7. Prepare PostgreSQL configuration and migration rehearsal on synthetic data;
   document SQLite-to-PostgreSQL cutover and rollback. Do not migrate real data
   under this work order without separate approval.
8. Implement encrypted backups, retention, access control and restore drill.
   Record agreed RPO/RTO and measured recovery results.
9. Add reverse-proxy guidance for HTTPS, HSTS, CSP, secure headers, request
   limits, trusted proxy handling and CORS.
10. Write deploy, rollback, incident response, user recovery, database recovery
    and key-rotation runbooks.

## Gate 4 acceptance

1. Clean checkout builds and tests in CI without local-only assumptions.
2. Container runs non-root and passes image/security scans within approved
   thresholds.
3. Staging deployment, migration, smoke test and rollback are repeatable.
4. Restore drill meets approved RPO/RTO using synthetic/staging data.
5. Logs/metrics expose failures without leaking secrets or sensitive records.
6. Security headers and TLS configuration pass the approved staging check.
7. `git diff --check`, full regression suite and CVF Doctor PASS.
8. Human operations/security release review approves Gate 4.

## Stop and escalate

Stop if production credentials/data are required, the hosting target is
undefined, RPO/RTO lacks owner approval, or a release would bypass staging and
human approval.

## Delivery report

Include image digest, CI run, scan summaries, staging evidence, measured RPO/
RTO, runbook links, residual risks and final commit/Doctor status. Passing Gate
4 is not itself authorization to release production.
