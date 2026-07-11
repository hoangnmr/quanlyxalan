import json
import sqlite3

from scripts.backup_local import backup, prune
from scripts.restore_local import restore


def test_sqlite_backup_has_manifest_and_integrity(tmp_path):
    source = tmp_path / "source.db"
    destination = tmp_path / "backup.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO sample(value) VALUES ('ok')")
        db.commit()

    manifest_path = backup(source, destination)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["integrity_check"] == "ok"
    assert len(manifest["sha256"]) == 64
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "ok"

    restored = tmp_path / "restored.db"
    restore(destination, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "ok"


def test_backup_retention_prunes_old_snapshots(tmp_path):
    for day in range(1, 40):
        item = tmp_path / f"cang_vu-202501{day:02d}-010101.db"
        item.write_bytes(b"db")
    removed = prune(tmp_path, keep_daily=2, keep_monthly=1, keep_annual=1)
    assert removed
    assert len(list(tmp_path.glob("*.db"))) <= 2
