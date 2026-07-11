import json
import sqlite3

from scripts.backup_local import backup


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
