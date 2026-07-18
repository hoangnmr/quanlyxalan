import json
import os
import sqlite3
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from .models import Base, AuditEvent

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enforce foreign keys on every SQLite connection.

    SQLite disables foreign-key enforcement by default, so declared foreign keys
    and ON DELETE CASCADE are silently ignored. This global connect hook turns
    enforcement on for the application engine, the Alembic migration engine and
    any test engine created in this process. It is scoped to SQLite connections
    only, so a non-SQLite backend is unaffected.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cang_vu.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Allow test suite to override database URL via environment variable
# set BEFORE importing this module (e.g. in conftest.py or test file preamble)
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", f"sqlite:///{DB_PATH}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def audit(
    db, entity_type: str, entity_id: int, action: str, summary: str,
    *, actor_user_id: int | None = None, organization_id: int | None = None,
    reporting_unit_id: int | None = None,
) -> None:
    # ``organization_id`` is always a customer Organization; a Port is recorded
    # separately via ``reporting_unit_id`` so the two are never conflated.
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        summary=summary[:500],
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        reporting_unit_id=reporting_unit_id,
        correlation_id=correlation_id.get(),
        created_at=now_iso()
    )
    db.add(event)

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

def decode_declaration(item: dict[str, Any]) -> dict[str, Any]:
    item["unload"] = json.loads(item.pop("unload_json", "{}"))
    item["load"] = json.loads(item.pop("load_json", "{}"))
    return item
