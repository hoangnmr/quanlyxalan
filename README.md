# Port Declaration System

Web application for TIEN-TAN THUAN PORT customer declarations, vessel and crew
certificate tracking, attachments, and periodic Maritime Administration reporting.

## Run locally

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-dev.ps1
```

Open `http://127.0.0.1:8080`.

The application uses Python 3.11+ standard-library modules only. The SQLite
database is created at `data/cang_vu.db` and is intentionally ignored by Git.

## Production boundary

Use a persistent volume for `data/`, HTTPS through the company reverse proxy,
and company authentication before accepting real customer data. See
`docs/ARCHITECTURE.md` and `docs/DEPLOYMENT.md`.
