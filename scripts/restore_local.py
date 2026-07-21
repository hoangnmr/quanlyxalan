"""Restore a verified PostgreSQL backup only after explicit operator confirmation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _libpq_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def restore(source: Path, url: str) -> None:
    """Verify the archive against its manifest, then restore it into ``url``."""
    manifest_path = source.with_suffix(source.suffix + ".manifest.json")
    if not manifest_path.exists():
        raise RuntimeError("Backup manifest không tồn tại.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest.get("sha256"):
        raise RuntimeError("Checksum backup không khớp manifest.")
    try:
        subprocess.run(
            [
                "pg_restore",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--exit-on-error",
                "--dbname",
                _libpq_url(url),
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pg_restore không có trong PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Restore thất bại: {exc.stderr.strip()}") from exc


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--url", default=None, help="Target PostgreSQL URL (default: app configuration)")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "RESTORE":
        raise SystemExit("Đặt --confirm RESTORE để thực hiện khôi phục.")
    if args.url:
        url = args.url
    else:
        from backend.database import SQLALCHEMY_DATABASE_URL

        url = os.environ.get("DATABASE_URL") or SQLALCHEMY_DATABASE_URL
    restore(args.source, url)
    print(url)


if __name__ == "__main__":
    main()
