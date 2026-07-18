from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import now_iso
from backend.models import Base, Organization, User, Vessel


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap_reporting_unit.py"


def _run(database: Path, *, apply: bool = False) -> dict:
    command = [
        sys.executable, str(SCRIPT),
        "--database", str(database),
        "--unit-name", "Test Port",
        "--unit-code", "TEST-PORT",
        "--staff-username", "portstaff",
        "--actor-username", "platform",
        "--all-organizations",
        "--map-legacy-tracked",
    ]
    if apply:
        command.append("--apply")
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def test_bootstrap_reporting_unit_is_dry_run_safe_and_idempotent(tmp_path):
    database = tmp_path / "bootstrap.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        organization = Organization(name="Customer", created_at=now_iso(), updated_at=now_iso())
        session.add(organization)
        session.flush()
        session.add_all([
            User(username="platform", password_hash="hash", role="PLATFORM_ADMIN", is_active=1, created_at=now_iso()),
            User(username="portstaff", password_hash="hash", role="PORT_STAFF", is_active=1, created_at=now_iso()),
            Vessel(
                organization_id=organization.id, name="Legacy", registration_no="LEGACY-1",
                vessel_type="Sà lan", vessel_class="VR-SI", is_port_tracked=1,
                created_at=now_iso(), updated_at=now_iso(),
            ),
        ])
        session.commit()
    engine.dispose()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('n13f0f000013')")
        connection.commit()

    preview = _run(database)
    assert preview["mode"] == "DRY_RUN"
    assert preview["after"]["unit_register_vessels"] == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM reporting_units").fetchone()[0] == 0

    applied = _run(database, apply=True)
    assert applied["mode"] == "APPLY"
    assert applied["after"]["unit_register_vessels"] == 1
    repeated = _run(database, apply=True)
    assert repeated["unit"]["created"] is False
    assert repeated["after"]["units"] == 1
    assert repeated["after"]["memberships"] == 1
    assert repeated["after"]["organization_links"] == 1
    assert repeated["after"]["register_links"] == 1
