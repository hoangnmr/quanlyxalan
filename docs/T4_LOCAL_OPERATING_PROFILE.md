# T4 Local-First Operating Profile

- Profile id: `KBCV-T4-LOCAL-1.0`
- Status: APPROVED FOR LOCAL IMPLEMENTATION
- Approval date: 2026-07-11
- Production readiness claim: NOT AUTHORIZED

## Deployment boundary

- Hosting and public domain are intentionally deferred.
- T4 verification targets local development and local integration testing only.
- HTTPS, public ingress, staging deployment and production release gates remain
  open until infrastructure owners are assigned.

## Database

- SQLite remains the pilot database.
- The database must stay on a local persistent filesystem with reliable locking.
- PostgreSQL cutover remains a future governed migration; application code must
  avoid SQLite-specific business semantics where practical.

## Object storage

- Target interface: MinIO/S3-compatible object storage.
- Local mode may use a MinIO container or a disabled adapter when MinIO is not
  installed; credentials must come from environment/secret storage.
- No application-level storage quota is imposed initially, but “unlimited” is
  treated as capacity-managed rather than physically unlimited.
- Alert thresholds: warning at 70%, high at 85%, critical at 95% capacity.
- Business/reporting data is retained indefinitely until a formal disposal
  policy is approved.
- ADMIN may request backup/restore; restore operations require an explicit
  confirmation, immutable audit event and post-restore integrity check.

## Backup, RPO and RTO

- RPO: 24 hours.
- RTO: 4 hours.
- Automatic backup: daily.
- Manual backup/restore: ADMIN/Operator only.
- Retention: 30 daily backups, 12 monthly backups and one annual snapshot.
- Backup artifacts require checksum manifests and encryption when stored outside
  the local trusted host.
- Restore drill: quarterly using a copy, never by overwriting the active database.
- A backup is not considered valid until a restore and integrity check succeeds.

## CI/CD baseline

- Platform: GitHub Actions.
- Required checks: format, lint, type check, unit/integration tests, migration
  rehearsal, dependency audit, SAST, secret scan and artifact checks.
- Local test evidence remains the active release boundary until staging exists.
- Production deployment jobs must remain disabled/manual until a deployment
  target and approver are documented.

## Logging and alerting

- Operational logs: structured local JSON files with size/time rotation.
- Operational log retention: 180 days.
- Security/authentication log retention: 2 years.
- Immutable audit events and declaration history: minimum 7 years; business
  data remains indefinite under the current reporting requirement.
- Logs must redact passwords, bearer tokens, secrets and attachment content.
- Alert channels: email and Microsoft Teams. Connector credentials are deferred
  and must never be committed.

## Roles and approvals

- ADMIN: application administration, user/data governance, approved backup and
  restore requests.
- Operator: runtime operation, backup execution, restore drill and incident
  handling.
- For destructive restore, ADMIN requests and Operator executes; the same person
  should not approve and execute when staffing permits.
- Local release approval: ADMIN or designated Operator after all automated gates.

## Security and lifecycle policy selected by EA review

- JWT/signing secrets: rotate at least every 90 days and immediately after a
  suspected compromise.
- Disabled accounts lose access immediately; deletion is avoided when records
  are referenced by audit history.
- Dependency review: monthly and before each release.
- Access review: quarterly for ADMIN, Operator, CV, QLC and BP roles.
- Incident classification:
  - SEV-1: data loss, unauthorized disclosure or service-wide compromise.
  - SEV-2: major workflow outage or failed restore.
  - SEV-3: degraded function with workaround.
- SEV-1 requires immediate containment, credential rotation assessment, backup
  preservation and owner notification.
- All backup, restore, role changes and configuration changes must be audited.

## Management dashboards required

The product roadmap must include ADMIN/management tabs for:

1. Operational volume: declarations, arrivals/departures, cargo tons/TEU and
   passenger counts over selectable periods.
2. Workflow SLA: pending by stage, aging buckets, change requests and revoked
   permits.
3. Fleet/certificate health: active vessels, expiring/expired certificates and
   crew qualification warnings.
4. Import/report quality: accepted/rejected rows, report counts and mapping
   versions.
5. Storage/backup: SQLite size, object count/bytes, last successful backup,
   restore drill status and capacity thresholds.
6. Security: login failures, disabled users, privileged actions and unresolved
   audit anomalies.

Dashboard data must obey RBAC, tenant isolation and the reporting mapping spec.

## Open blockers before full Gate 4

- Hosting target and operating system.
- Domain, DNS, TLS and reverse proxy.
- Staging environment and independent smoke/rollback run.
- Actual MinIO endpoint and secret provisioning.
- Email/Teams connector configuration.
- Named production release and incident owners.

Until these are supplied, T4 may achieve LOCAL_GATE_PASS only, not full Gate 4
or production readiness.
