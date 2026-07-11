from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cang_vu.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                tax_code TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                contact_name TEXT NOT NULL DEFAULT '',
                contact_role TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vessels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER REFERENCES organizations(id),
                name TEXT NOT NULL,
                registration_no TEXT NOT NULL UNIQUE,
                registry_or_imo TEXT NOT NULL DEFAULT '',
                vessel_type TEXT NOT NULL,
                vessel_class TEXT NOT NULL,
                shell_material TEXT NOT NULL DEFAULT '',
                build_year INTEGER,
                length_m REAL,
                width_m REAL,
                side_height_m REAL,
                draft_m REAL,
                deadweight_tons REAL,
                gross_tonnage REAL,
                engine_power_cv REAL,
                cargo_capacity_tons REAL,
                container_capacity_teu REAL,
                passenger_capacity INTEGER,
                min_crew INTEGER,
                safety_certificate_no TEXT NOT NULL DEFAULT '',
                certificate_issue_date TEXT,
                certificate_expiry_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS declarations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_no TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'DRAFT',
                organization_id INTEGER REFERENCES organizations(id),
                vessel_id INTEGER REFERENCES vessels(id),
                declaration_date TEXT NOT NULL,
                company_name TEXT NOT NULL,
                vessel_name TEXT NOT NULL,
                registration_no TEXT NOT NULL,
                vessel_type TEXT NOT NULL,
                vessel_class TEXT NOT NULL,
                length_m REAL,
                deadweight_tons REAL,
                gross_tonnage REAL,
                certificate_expiry_date TEXT,
                crew_count INTEGER NOT NULL DEFAULT 0,
                passenger_count INTEGER NOT NULL DEFAULT 0,
                last_port TEXT NOT NULL,
                working_port TEXT NOT NULL,
                destination_port TEXT NOT NULL DEFAULT '',
                eta TEXT NOT NULL,
                etd TEXT NOT NULL,
                unload_json TEXT NOT NULL,
                load_json TEXT NOT NULL,
                master_name TEXT NOT NULL,
                master_phone TEXT NOT NULL,
                submitted_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_vessel_org ON vessels(organization_id);
            CREATE INDEX IF NOT EXISTS idx_declaration_dates ON declarations(eta, etd);
            CREATE INDEX IF NOT EXISTS idx_declaration_status ON declarations(status);
            """
        )


def rows_to_dicts(rows: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def audit(db: sqlite3.Connection, entity_type: str, entity_id: int, action: str, summary: str) -> None:
    db.execute(
        "INSERT INTO audit_events(entity_type, entity_id, action, summary, created_at) VALUES(?,?,?,?,?)",
        (entity_type, entity_id, action, summary[:500], now_iso()),
    )


def cargo(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    numbers = {}
    for key in ("cont20_full", "cont20_empty", "cont40_full", "cont40_empty"):
        try:
            numbers[key] = max(0, int(source.get(key) or 0))
        except (TypeError, ValueError):
            numbers[key] = 0
    total = sum(numbers.values())
    teu = numbers["cont20_full"] + numbers["cont20_empty"] + 2 * (
        numbers["cont40_full"] + numbers["cont40_empty"]
    )
    empty_teu = numbers["cont20_empty"] + 2 * numbers["cont40_empty"]
    try:
        tons = max(0.0, float(source.get("tons") or 0))
    except (TypeError, ValueError):
        tons = 0.0
    return {
        "cargo_type": str(source.get("cargo_type") or ""),
        "movement_type": str(source.get("movement_type") or ""),
        "cargo_name": str(source.get("cargo_name") or ""),
        **numbers,
        "total_containers": total,
        "teu": teu,
        "empty_teu": empty_teu,
        "tons": tons,
    }


def decode_declaration(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["unload"] = json.loads(item.pop("unload_json"))
    item["load"] = json.loads(item.pop("load_json"))
    return item

