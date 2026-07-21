# Security Boundary — Quan-Ly-Xalan

This document details the security constraints, architecture, and threat mitigation measures implemented in the system as of **WO-KBCV-T1-20260711**.

---

## 1. Identity & Session Design

*   **Authentication Mechanism**: Stateless JWT Bearer tokens passed via HTTP `Authorization: Bearer <token>` header.
*   **Storage**: Client stores token in `localStorage`.
*   **Token Lifetime**: Expire time defaults to **24 hours** (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
*   **Session Revocation**: Handled via `POST /api/auth/logout` and validated against client-side token deletion. Session expiry triggers a redirection to the login dialog.
*   **Fail-Fast Key check**: The application aborts startup (`SystemExit`) if `SECRET_KEY` is not set or matches the development default outside the explicit test environment.

---

## 2. Role-Based Access Control (RBAC)

RBAC is enforced on the server-side via Python dependencies:
*   `require_roles(*roles)`: Matches the user's role claim in the JWT against allowed endpoint roles.
*   `get_current_user`: Resolves the session and verifies `is_active == 1`. Disabled users are blocked instantly.

### Workflow Transition Matrix
The workflow state machine is protected against unauthorized state jumps:
*   `CUSTOMER`: Can only create drafts and submit own declarations.
*   `CV`: Can only perform `CV_APPROVE` and `REQUEST_CHANGES`.
*   `QLC`: Can only perform `QLC_APPROVE` and `REQUEST_CHANGES`.
*   `BP`: Can only perform `BP_APPROVE`, `ISSUE`, `REVOKE`, and `REQUEST_CHANGES`.
*   `ADMIN`: **Explicitly denied** from performing any workflow state changes.

### Audit Integrity
To prevent client-side impersonation:
*   Client-supplied `actor_name` and `actor_role` are **ignored** by the `/api/declarations/{id}/workflow` endpoint.
*   The system extracts the actor identity directly from the authenticated JWT user session (`User.full_name` and `User.role`) when committing events to the database history.

---

## 3. Tenant Isolation & IDOR Protection

Tenant isolation prevents cross-organization data leakage.
*   **Partition Key**: `users.organization_id`.
*   **Ownership Check**: Egress / ingress endpoints call `verify_organization_ownership(user, resource_organization_id)` to validate that the resource belongs to the user's organization.
*   **Guessed ID Protection**: Any cross-tenant data access attempts (via guessed or sequential IDs) return a `403 Forbidden` error immediately, preventing IDOR (Insecure Direct Object Reference).
*   **Global Access Roles**: Users with roles `CV`, `QLC`, `BP`, and `ADMIN` are treated as global system reviewers/operators and bypass tenant-filtering for views, but are subject to strict functional boundaries.

---

## 4. Operational Hardening

### Login Rate Limiting (Brute-Force Protection)
An in-memory IP-based rate limiter protects `/api/auth/login`:
*   **Threshold**: Maximum of **5 failed login attempts** per IP.
*   **Lockout**: The source IP is blocked for **5 minutes** on the 6th failed attempt.
*   **Response**: Returns HTTP `429 Too Many Requests`.

### CORS Configuration
Cross-Origin Resource Sharing (CORS) is configured to limit API access:
*   Origins are parsed from the `ALLOWED_ORIGINS` environment variable (comma-separated list).
*   Defaults to localhost development endpoints: `http://127.0.0.1:8080,http://localhost:8080`.
