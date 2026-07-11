# ADR-002: JWT Bearer and Local Session Design for Pilot

**Status**: ACCEPTED
**Date**: 2026-07-11
**Context**: Tranche T1 (WO-KBCV-T1-20260711)
**Author**: Antigravity

## Context

The Tan Thuan Port customer declaration system requires secure authentication and session management. We need to decide between:
1. **Stateless JWT Bearer token** stored in `localStorage`
2. **Secure HTTP-only cookies** managed via a Backend-for-Frontend (BFF) session structure.

## Decision

For the local single-node pilot phase, we select **Option 1: Stateless JWT Bearer token stored in `localStorage`**.

### Mitigation for localStorage Security Risks
To minimize the exposure of `localStorage` to Cross-Site Scripting (XSS) attacks:
1. **Short Token Lifetime**: Tokens expire in 24 hours by default, and this lifetime is configurable via the `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable.
2. **Strict CORS Allowlist**: CORS origins will be strictly validated based on the `ALLOWED_ORIGINS` environment variable, avoiding wildcard `*` settings in non-local environments.
3. **No Sensitive Claims in JWT**: The JWT payload only contains public identification fields (`sub` / username, `role`, and `org_id`). It never contains password hashes, database keys, or PII.

## Consequences

- The frontend (`app.js`) will continue to read the token from `localStorage` and supply it via the `Authorization: Bearer <token>` header.
- Token revocation is stateless (until T4). Logout is accomplished client-side by clearing the token from storage.
- T4 will re-evaluate migrating to HTTP-only cookies if the production environment requires protection against all localStorage-accessible XSS vectors.
