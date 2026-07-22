import json
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, AuditEvent

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".env").exists():
    load_dotenv(dotenv_path=ROOT / ".env")

DEFAULT_DATABASE_URL = "postgresql+psycopg://localhost/cangvu"

# ``TEST_DATABASE_URL`` takes precedence and must be set BEFORE this module is
# imported (test modules do so in their preamble). ``DATABASE_URL`` is the
# normal deployment knob; both must point at PostgreSQL.
SQLALCHEMY_DATABASE_URL = (
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or DEFAULT_DATABASE_URL
)

if not SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    raise RuntimeError(
        "This application requires PostgreSQL. "
        f"Unsupported database URL: {SQLALCHEMY_DATABASE_URL!r}"
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
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
    unit_tons = {}
    for key in ("tons20_full", "tons20_empty", "tons40_full", "tons40_empty"):
        try:
            unit_tons[key] = max(0.0, float(source.get(key) or 0))
        except (TypeError, ValueError):
            unit_tons[key] = 0.0
    try:
        tons = max(0.0, float(source.get("tons") or 0))
    except (TypeError, ValueError):
        tons = 0.0
    return {
        "cargo_type": str(source.get("cargo_type") or ""),
        "movement_type": str(source.get("movement_type") or ""),
        "cargo_name": str(source.get("cargo_name") or ""),
        **numbers,
        **unit_tons,
        "total_containers": total,
        "teu": teu,
        "empty_teu": empty_teu,
        "tons": tons,
    }

def decode_declaration(item: dict[str, Any]) -> dict[str, Any]:
    item["unload"] = json.loads(item.pop("unload_json", "{}"))
    item["load"] = json.loads(item.pop("load_json", "{}"))
    return item
