import json

from sqlalchemy import create_engine, text

from scripts.backup_local import BACKUP_SUFFIX, backup, prune
from scripts.restore_local import restore


def test_postgres_backup_has_manifest_and_integrity(pg_url, tmp_path):
    destination = tmp_path / f"backup{BACKUP_SUFFIX}"
    engine = create_engine(pg_url)
    with engine.begin() as db:
        db.execute(text("CREATE TABLE sample(id SERIAL PRIMARY KEY, value TEXT)"))
        db.execute(text("INSERT INTO sample(value) VALUES ('ok')"))
    engine.dispose()

    manifest_path = backup(pg_url, destination)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["integrity_check"] == "ok"
    assert len(manifest["sha256"]) == 64

    # Restoring over the same database must reproduce the seeded row.
    restore(destination, pg_url)
    engine = create_engine(pg_url)
    with engine.connect() as db:
        assert db.execute(text("SELECT value FROM sample")).scalar() == "ok"
    engine.dispose()


def test_backup_retention_prunes_old_snapshots(tmp_path):
    for day in range(1, 40):
        item = tmp_path / f"cang_vu-202501{day:02d}-010101{BACKUP_SUFFIX}"
        item.write_bytes(b"db")
    removed = prune(tmp_path, keep_daily=2, keep_monthly=1, keep_annual=1)
    assert removed
    assert len(list(tmp_path.glob(f"*{BACKUP_SUFFIX}"))) <= 2
