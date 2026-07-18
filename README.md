# Port Declaration System

Web application for TAN THUAN PORT customer declarations, vessel and crew
certificate tracking, attachments, and periodic Maritime Administration reporting.

## 📖 Hướng Dẫn Sử Dụng

**Người dùng cuối**: Xem [USER_GUIDE.md](USER_GUIDE.md) để hướng dẫn đầy đủ về các tính năng và cách sử dụng ứng dụng.

## Requirements

- Python 3.13 or newer
- pip (standard)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

All tests must pass before deploying or committing.

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-dev.ps1
```

The launcher applies Alembic migrations before starting the server. Set a
non-default `SECRET_KEY` in your local environment before running the service.

Or manually:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080 --reload
```

Open `http://127.0.0.1:8080`.

The application uses FastAPI + SQLAlchemy with SQLite at `data/cang_vu.db` (local dev).
The `data/` directory is intentionally ignored by Git.

## Architecture

Start with [CATALOG.md](CATALOG.md) for a full technical index (module map,
API route index, data model, docs map, "where do I change X" lookup). For
narrative detail see `docs/ARCHITECTURE.md` and `docs/ADR-001-FASTAPI-MIGRATION.md`.

## Production boundary

Use a persistent volume for `data/`, HTTPS through a reverse proxy, and
environment-supplied secrets (no hardcoded credentials). See `docs/DEPLOYMENT.md`
and the EA remediation roadmap at `docs/EA_EVALUATION_ROADMAP.md` for the
full path to production readiness (T0–T6).

1. SECRET_KEY: 
python -c "import secrets; print(secrets.token_hex(32))"

2. RUN (terminal)
$env:SECRET_KEY="your-secure-random-secret-key-32-chars-long"
powershell -ExecutionPolicy Bypass -File scripts\run-dev.ps1 -Port 8081
