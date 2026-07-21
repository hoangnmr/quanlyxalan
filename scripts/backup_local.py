"""Create local PostgreSQL backups with a verified manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BACKUP_SUFFIX = ".dump"
BACKUP_GLOB = f"cang_vu-*{BACKUP_SUFFIX}"


def database_url() -> str:
    """Resolve the database URL the same way the application does."""
    from backend.database import SQLALCHEMY_DATABASE_URL

    return SQLALCHEMY_DATABASE_URL


def _libpq_url(url: str) -> str:
    """Strip the SQLAlchemy driver marker so libpq tools accept the URL."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def backup(url: str, destination: Path) -> Path:
    """Dump the database in custom format and write a checksum manifest."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["pg_dump", "--format=custom", "--file", str(destination), _libpq_url(url)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pg_dump không có trong PATH.") from exc
    except subprocess.CalledProcessError as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump thất bại: {exc.stderr.strip()}") from exc

    # pg_restore --list only succeeds on a well-formed archive, so it doubles as
    # an integrity check on the file we just wrote.
    try:
        subprocess.run(
            ["pg_restore", "--list", str(destination)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {exc.stderr.strip()}") from exc

    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = destination.with_suffix(destination.suffix + ".manifest.json")
    manifest.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": _libpq_url(url).rsplit("/", 1)[-1],
        "backup": destination.name,
        "sha256": digest,
        "integrity_check": "ok",
    }, indent=2), encoding="utf-8")
    return manifest


def prune(backups_dir: Path, keep_daily: int = 30, keep_monthly: int = 12, keep_annual: int = 1) -> list[Path]:
    """Retain recent daily plus latest snapshots for each month/year."""
    files = sorted(backups_dir.glob(BACKUP_GLOB), key=lambda item: item.stat().st_mtime, reverse=True)
    keep: set[Path] = set(files[:keep_daily])
    months: set[str] = set()
    years: set[str] = set()
    for item in files:
        stamp = item.stem.removeprefix("cang_vu-")
        month, year = stamp[:6], stamp[:4]
        if len(months) < keep_monthly and month not in months:
            keep.add(item)
            months.add(month)
        if len(years) < keep_annual and year not in years:
            keep.add(item)
            years.add(year)
    removed: list[Path] = []
    for item in files:
        if item not in keep:
            manifest = item.with_suffix(item.suffix + ".manifest.json")
            item.unlink(missing_ok=True)
            manifest.unlink(missing_ok=True)
            removed.append(item)
    return removed


def main() -> None:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=None, help="PostgreSQL URL (default: app configuration)")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    url = args.url or os.environ.get("DATABASE_URL") or database_url()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = args.destination or Path("data/backups") / f"cang_vu-{stamp}{BACKUP_SUFFIX}"
    print(backup(url, destination))
    if args.prune:
        print(f"pruned={len(prune(destination.parent))}")


if __name__ == "__main__":
    main()
