# User Setup & Bootstrap Instructions — Khai-bao-Cang-vu

This document details the configuration requirements, database migrations, and administrative user bootstrapping for the system.

---

## 1. Environment Configuration

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Description | Default / Example | Security Requirement |
|----------|-------------|-------------------|----------------------|
| `SECRET_KEY` | JWT signing key | *random high-entropy string* | **Must be changed in production** (triggers exit if unchanged) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity duration | `60` | Low token lifetime limits hijacking risk |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://127.0.0.1:8080,http://localhost:8080` | Limits third-party script execution |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///data/cang_vu.db` | System storage path |
| `ADMIN_USERNAME` | Administrator bootstrap username | `admin` | Required for admin script |
| `ADMIN_PASSWORD` | Administrator bootstrap password | *secure_password* | Required for admin script |
| `ADMIN_FULL_NAME` | Administrator display name | `Admin Cảng vụ` | Required for admin script |

---

## 2. Database Migrations (Alembic)

Database schema updates must be applied using Alembic.

### Running Migrations
To upgrade the database to the latest schema:
```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

To roll back the last migration:
```powershell
.\venv\Scripts\python.exe -m alembic downgrade -1
```

To revert to the initial base schema:
```powershell
.\venv\Scripts\python.exe -m alembic downgrade base
```

*Note: Migrations utilize Alembic batch operations to safely add/drop columns and constraints in SQLite databases.*

---

## 3. Bootstrapping the Administrator Account

To configure the initial administrator without hardcoding passwords, use the bootstrap script.

### Pre-requisites
Make sure you have configured the following variables in `.env`:
*   `ADMIN_USERNAME`
*   `ADMIN_PASSWORD`
*   `ADMIN_FULL_NAME`

### Run Script
Execute the script from the project root:
```powershell
.\venv\Scripts\python.exe scripts/bootstrap_admin.py
```

### Safety and Security Behavior
*   **No Defaults**: The script **fails** if variables are missing from the environment.
*   **Idempotency**: If the user already exists, it updates their password hash safely.
*   **Unbound Users Cleanup**: To prevent orphan credentials, the database migration automatically **disables** (`is_active = 0`) any existing non-admin users who are not bound to an organization.
