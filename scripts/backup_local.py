"""Create or restore local SQLite backups without copying a live DB file."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {integrity}")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest = destination.with_suffix(destination.suffix + ".manifest.json")
    manifest.write_text(json.dumps({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source.name,
        "backup": destination.name,
        "sha256": digest,
        "integrity_check": integrity,
    }, indent=2), encoding="utf-8")
    return manifest


def prune(backups_dir: Path, keep_daily: int = 30, keep_monthly: int = 12, keep_annual: int = 1) -> list[Path]:
    """Retain recent daily plus latest snapshots for each month/year."""
    files = sorted(backups_dir.glob("cang_vu-*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/cang_vu.db"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = args.destination or Path("data/backups") / f"cang_vu-{stamp}.db"
    print(backup(args.source, destination))
    if args.prune:
        print(f"pruned={len(prune(destination.parent))}")


if __name__ == "__main__":
    main()
