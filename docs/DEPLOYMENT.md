# Deployment Notes

## Pilot

Run the Python service behind the company HTTPS reverse proxy. Proxy `/api/`
and the frontend routes to the same service, or serve `frontend/` directly and
proxy only `/api/`.

The `data/` directory must be a persistent, backed-up volume. SQLite is suitable
for the initial single-host workload. Do not place the database on an
ephemeral container filesystem or a network filesystem with unreliable locks.

## Required Before Production Customer Use

- Company SSO or approved account/password authentication.
- Role enforcement for customer, port reviewer, and administrator.
- HTTPS, secure headers, request throttling, and upload-size enforcement at the
  reverse proxy.
- Encrypted backups, restore drill, retention policy, and access logging.
- Operator review of the Appendix field mapping against the signed reporting
  instructions.
- Privacy notice and customer consent language approved by the company.
- Persistent `data/uploads/` storage plus malware scanning and quarantine.
- Official Maritime Authority API specification, test environment, credentials,
  retry/idempotency rules, and signed data-sharing approval before enabling send.
- External registry API authority and matching rules before presenting a check
  as registry-verified; local date checks must remain labelled as local.

The current MVP does not claim production or legal-approval readiness.
