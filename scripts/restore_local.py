"""Restore a verified SQLite backup only after explicit operator confirmation."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def restore(source: Path, destination: Path) -> None:
    manifest_path = source.with_suffix(source.suffix + ".manifest.json")
    if not manifest_path.exists():
        raise RuntimeError("Backup manifest không tồn tại.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest.get("sha256"):
        raise RuntimeError("Checksum backup không khớp manifest.")
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"Restore integrity check failed: {integrity}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != "RESTORE":
        raise SystemExit("Đặt --confirm RESTORE để thực hiện khôi phục.")
    restore(args.source, args.destination)
    print(args.destination)


if __name__ == "__main__":
    main()
