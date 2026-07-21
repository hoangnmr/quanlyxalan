"""tests/test_historical_import.py — H2 historical/TOS import store (R2 corrected)

Schema, migration, FK-backed tenant membership, fail-closed actor/reviewer
authorization, tenant-scoped audit and provenance coverage. H2 is schema/service
level only (no parser, API or UI); these tests exercise the models, the Alembic
migration, real PostgreSQL foreign-key enforcement and the service validators.

The tenant is a distinct ``ReportingUnit`` (a Port). Membership is FK-backed
(``reporting_unit_users`` / ``reporting_unit_organizations``) rather than a soft
column, and historical facts use composite tenant foreign keys. Negative tests
perform a forbidden operation and assert an ``IntegrityError`` or an explicit
fail-closed validation error.

Correction-order R2 coverage (docs/CLAUDE_H2_CORRECTION_ORDER_R2_20260718.md §11):
  membership FK: nonexistent unit/user/org -> test_membership_requires_existing_*
  actor: PORT_STAFF/tenant-ADMIN on foreign import, CUSTOMER, inactive,
         platform-ADMIN w/o context, valid membership, platform w/ context
         -> test_import_actor_*
  reviewer: valid, cross-port -> test_reviewer_*
  candidate vessel: other-port-only membership, multi-port -> test_vessel_link_*
  audit: nonexistent unit, correct scope, no org/port conflation -> test_audit_*
  drift: missing secondary composite constraint -> test_schema_drift_*
  Plus retained: composite cross-tenant rejections, cascade-by-SQL, ATB/ATD,
  blank/zero/invalid, fresh + pre-H2 migration preservation.
"""
from __future__ import annotations

import importlib.util
import os
import tempfile
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# ── Hermetic engine, independent of the shared test DB used by other files ────
from tests import _pgdb

_DB_URL = _pgdb.create_database("kbcv_hist")
os.environ["TEST_DATABASE_URL"] = _DB_URL

import backend.database  # noqa: E402,F401
from backend.database import now_iso, audit  # noqa: E402
from backend.historical import (  # noqa: E402
    validate_vessel_link_tenant,
    validate_import_actor,
    validate_reviewer,
    HistoricalTenantError,
    HistoricalAuthorizationError,
)
from backend.models import (  # noqa: E402
    Base,
    Organization,
    ReportingUnit,
    ReportingUnitUser,
    ReportingUnitOrganization,
    User,
    Vessel,
    AuditEvent,
    HistoricalReportImport,
    HistoricalReportRow,
    HistoricalReportMetric,
    HistoricalPortCall,
    HistoricalCargoRow,
    HistoricalVesselLink,
)

_engine = create_engine(_DB_URL)
Base.metadata.create_all(bind=_engine)
_Session = sessionmaker(bind=_engine)

ALEMBIC_INI = str(Path(__file__).resolve().parents[1] / "alembic.ini")
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "m12f0f000012_historical_tos_import_store.py"
HISTORICAL_TABLES = {
    "historical_report_imports",
    "historical_report_rows",
    "historical_report_metrics",
    "historical_port_calls",
    "historical_cargo_rows",
    "historical_vessel_links",
}
MEMBERSHIP_TABLES = {"reporting_unit_users", "reporting_unit_organizations"}


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("m12_under_test", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def session():
    db = _Session()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def _unit(db, name: str | None = None, *, is_active: int = 1) -> ReportingUnit:
    unit = ReportingUnit(
        name=name or f"Port {_uid()}", is_active=is_active, created_at=now_iso(), updated_at=now_iso()
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def _user(db, role: str = "PORT_STAFF", *, is_active: int = 1) -> User:
    user = User(username=f"u_{_uid()}", password_hash="x", role=role, is_active=is_active, created_at=now_iso())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _add_user_membership(db, unit_id: int, user_id: int) -> None:
    db.add(ReportingUnitUser(reporting_unit_id=unit_id, user_id=user_id, created_at=now_iso()))
    db.commit()


def _add_org_membership(db, unit_id: int, org_id: int) -> None:
    db.add(ReportingUnitOrganization(reporting_unit_id=unit_id, organization_id=org_id, created_at=now_iso()))
    db.commit()


def _org(db) -> Organization:
    org = Organization(name=f"Cust {_uid()}", created_at=now_iso(), updated_at=now_iso())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _vessel(db, org_id: int) -> Vessel:
    vessel = Vessel(
        organization_id=org_id, name="Canonical", registration_no=f"REG-{_uid()}",
        vessel_type="Sa lan", vessel_class="VR-SI", created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return vessel


def _import(db, unit_id: int, user_id: int, *, checksum: str,
            source_kind: str = "tos_berth_call", mapping_version: str = "tos_berth_v1",
            **kwargs) -> HistoricalReportImport:
    record = HistoricalReportImport(
        reporting_unit_id=unit_id, source_kind=source_kind, mapping_version=mapping_version,
        source_checksum=checksum, source_filename="provenance-only.xlsx", source_size_bytes=1000,
        created_by_user_id=user_id, created_at=now_iso(), updated_at=now_iso(), **kwargs,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── Migration coverage ────────────────────────────────────────────────────────

def _table_names(connection) -> set:
    return set(inspect(connection).get_table_names())


def test_fresh_database_upgrades_to_single_head(monkeypatch, pg_url):
    heads = ScriptDirectory.from_config(Config(ALEMBIC_INI)).get_heads()
    assert heads == ["q16f0f000016"], f"expected a single head, got {heads}"

    url = pg_url
    import backend.database as database
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", url)
    command.upgrade(Config(ALEMBIC_INI), "head")

    inspector = inspect(create_engine(url))
    tables = set(inspector.get_table_names())
    assert HISTORICAL_TABLES.issubset(tables)
    assert MEMBERSHIP_TABLES.issubset(tables)
    assert "reporting_units" in tables
    # Soft tenant columns are gone; audit gains a tenant FK column.
    assert "reporting_unit_id" not in {c["name"] for c in inspector.get_columns("organizations")}
    assert "reporting_unit_id" not in {c["name"] for c in inspector.get_columns("users")}
    assert "reporting_unit_id" in {c["name"] for c in inspector.get_columns("audit_events")}


def test_pre_h2_database_preserved_through_migration(monkeypatch, pg_url):
    """A hand-built pre-H2 database keeps every seeded live value across upgrade,
    downgrade and re-upgrade while m12 adds/removes only H2 structures."""
    url = pg_url
    legacy_engine = create_engine(url)
    with legacy_engine.begin() as c:
        c.execute(text("CREATE TABLE organizations (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, name VARCHAR NOT NULL UNIQUE, created_at VARCHAR, updated_at VARCHAR)"))
        c.execute(text("CREATE TABLE users (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, username VARCHAR NOT NULL UNIQUE, password_hash VARCHAR, role VARCHAR, organization_id INTEGER, is_active INTEGER, created_at VARCHAR)"))
        c.execute(text("CREATE TABLE vessels (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, organization_id INTEGER, name VARCHAR, registration_no VARCHAR UNIQUE, vessel_type VARCHAR, vessel_class VARCHAR)"))
        c.execute(text("CREATE TABLE declarations (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, reference_no VARCHAR UNIQUE, company_name VARCHAR, vessel_name VARCHAR)"))
        c.execute(text("CREATE TABLE audit_events (id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, entity_type VARCHAR, entity_id INTEGER, action VARCHAR, summary TEXT, actor_user_id INTEGER, organization_id INTEGER, correlation_id VARCHAR, created_at VARCHAR)"))
        c.execute(text("CREATE TABLE alembic_version (version_num VARCHAR NOT NULL)"))
        c.execute(text("INSERT INTO alembic_version VALUES ('l11f0f000011')"))
        c.execute(text("INSERT INTO organizations(id,name,created_at,updated_at) VALUES (7,'Legacy Co','t','t')"))
        c.execute(text("INSERT INTO users(id,username,password_hash,role,organization_id,is_active,created_at) VALUES (3,'legacy_admin','h','ADMIN',NULL,1,'t')"))
        c.execute(text("INSERT INTO vessels(id,organization_id,name,registration_no,vessel_type,vessel_class) VALUES (5,7,'Legacy Vessel','REG-L','Sa lan','VR-SI')"))
        c.execute(text("INSERT INTO declarations(id,reference_no,company_name,vessel_name) VALUES (9,'REF-9','Legacy Co','Legacy Vessel')"))
        c.execute(text("INSERT INTO audit_events(id,entity_type,entity_id,action,summary,created_at) VALUES (1,'user',1,'LOGIN_SUCCESS','ok','t')"))
    legacy_engine.dispose()

    import backend.database as database
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", url)
    config = Config(ALEMBIC_INI)

    command.upgrade(config, "head")
    with create_engine(url).connect() as c:
        tables = _table_names(c)
        assert HISTORICAL_TABLES.issubset(tables) and MEMBERSHIP_TABLES.issubset(tables)
        assert c.execute(text("select name from organizations where id=7")).scalar() == "Legacy Co"
        assert c.execute(text("select reference_no from declarations where id=9")).scalar() == "REF-9"
        assert c.execute(text("select action from audit_events where id=1")).scalar() == "LOGIN_SUCCESS"
        # Legacy ADMIN is migrated to PLATFORM_ADMIN (role-only; stays active).
        role, active = c.execute(text("select role, is_active from users where id=3")).one()
        assert role == "PLATFORM_ADMIN" and active == 1
        assert c.execute(text("select count(*) from users where role='ADMIN'")).scalar() == 0

    command.downgrade(config, "l11f0f000011")
    with create_engine(url).connect() as c:
        tables = _table_names(c)
        assert not ((HISTORICAL_TABLES | MEMBERSHIP_TABLES) & tables) and "reporting_units" not in tables
        assert "reporting_unit_id" not in {col["name"] for col in inspect(c).get_columns("audit_events")}
        assert c.execute(text("select name from organizations where id=7")).scalar() == "Legacy Co"
        assert c.execute(text("select action from audit_events where id=1")).scalar() == "LOGIN_SUCCESS"
        # Role reversal restores the legacy ADMIN role for pre-H2 compatibility.
        assert c.execute(text("select role from users where id=3")).scalar() == "ADMIN"

    command.upgrade(config, "head")
    with create_engine(url).connect() as c:
        tables = _table_names(c)
        assert HISTORICAL_TABLES.issubset(tables)


def test_schema_drift_missing_secondary_composite_is_rejected(pg_url):
    """The migration's fail-closed verification rejects a drifted schema that is
    missing a secondary composite constraint (cargo -> port call)."""
    engine = create_engine(pg_url)
    Base.metadata.create_all(bind=engine)
    # Replace historical_cargo_rows with a variant that keeps the import composite
    # FK but DROPS the cargo -> port_call composite FK.
    with engine.begin() as c:
        c.execute(text("DROP TABLE historical_cargo_rows CASCADE"))
        c.execute(text(
            "CREATE TABLE historical_cargo_rows ("
            " id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,"
            " reporting_unit_id INTEGER NOT NULL REFERENCES reporting_units(id),"
            " import_id INTEGER NOT NULL,"
            " source_sheet VARCHAR, source_row INTEGER,"
            " port_call_id INTEGER,"
            " weight_state VARCHAR DEFAULT 'PRESENT',"
            " transform_version VARCHAR,"
            " match_status VARCHAR DEFAULT 'PENDING',"
            " validation_status VARCHAR DEFAULT 'PENDING',"
            " created_at VARCHAR,"
            " CONSTRAINT fk_hist_cargo_import FOREIGN KEY (import_id, reporting_unit_id)"
            "   REFERENCES historical_report_imports(id, reporting_unit_id))"
        ))

    module = _load_migration_module()
    with engine.connect() as conn:
        with pytest.raises(RuntimeError) as excinfo:
            module._verify_tenant_schema(conn)
    assert "historical_cargo_rows" in str(excinfo.value)
    assert "port_call" in str(excinfo.value).lower()


def test_schema_verification_passes_on_correct_schema(pg_url):
    engine = create_engine(pg_url)
    Base.metadata.create_all(bind=engine)
    module = _load_migration_module()
    with engine.connect() as conn:
        module._verify_tenant_schema(conn)  # must not raise on a correct schema


# ── Distinct tenant entity and foreign-key enforcement ───────────────────────

def test_reporting_unit_is_distinct_entity_from_organization():
    assert ReportingUnit.__tablename__ == "reporting_units"
    assert Organization.__tablename__ == "organizations"
    assert ReportingUnit is not Organization
    # No soft tenant column survives on the customer/user tables.
    assert "reporting_unit_id" not in {c.name for c in Organization.__table__.columns}
    assert "reporting_unit_id" not in {c.name for c in User.__table__.columns}


def test_foreign_keys_enforced_on_connection():
    """PostgreSQL enforces declared foreign keys unconditionally; prove it by
    attempting a write that violates one."""
    with pytest.raises(IntegrityError):
        with _engine.begin() as c:
            c.execute(text(
                "INSERT INTO reporting_unit_users(reporting_unit_id,user_id,membership_role,created_at) "
                "VALUES (2147483000, 2147483000, '', :ts)"
            ), {"ts": now_iso()})


def test_foreign_key_check_is_clean(session):
    """Every foreign key on the historical tables is present and validated."""
    unit = _unit(session)
    user = _user(session)
    _add_user_membership(session, unit.id, user.id)
    _import(session, unit.id, user.id, checksum=f"clean-{_uid()}")
    with _engine.connect() as c:
        unvalidated = c.execute(text(
            "SELECT conname FROM pg_constraint WHERE contype='f' AND NOT convalidated"
        )).fetchall()
        assert unvalidated == []


# ── FK-backed membership rejects invalid ids ─────────────────────────────────

def test_membership_requires_existing_reporting_unit(session):
    user = _user(session)
    session.add(ReportingUnitUser(reporting_unit_id=999999, user_id=user.id, created_at=now_iso()))
    with pytest.raises(IntegrityError):
        session.commit()


def test_membership_requires_existing_user(session):
    unit = _unit(session)
    session.add(ReportingUnitUser(reporting_unit_id=unit.id, user_id=999999, created_at=now_iso()))
    with pytest.raises(IntegrityError):
        session.commit()


def test_org_membership_requires_existing_organization(session):
    unit = _unit(session)
    session.add(ReportingUnitOrganization(reporting_unit_id=unit.id, organization_id=999999, created_at=now_iso()))
    with pytest.raises(IntegrityError):
        session.commit()


# ── Idempotency and composite cross-tenant isolation (retained) ──────────────

def test_duplicate_checksum_in_one_unit_rejected(session):
    unit = _unit(session)
    user = _user(session)
    checksum = f"dup-{_uid()}"
    _import(session, unit.id, user.id, checksum=checksum)
    with pytest.raises(IntegrityError):
        _import(session, unit.id, user.id, checksum=checksum)


def test_same_checksum_allowed_across_reporting_units(session):
    unit_a, unit_b = _unit(session), _unit(session)
    user = _user(session)
    checksum = f"shared-{_uid()}"
    a = _import(session, unit_a.id, user.id, checksum=checksum)
    b = _import(session, unit_b.id, user.id, checksum=checksum)
    assert a.reporting_unit_id != b.reporting_unit_id


def _two_units_with_import(session):
    unit_a, unit_b = _unit(session), _unit(session)
    user_a = _user(session)
    imp_a = _import(session, unit_a.id, user_a.id, checksum=f"a-{_uid()}")
    return unit_a, unit_b, user_a, imp_a


def test_tenant_isolation_row_cannot_reference_foreign_import(session):
    unit_a, unit_b, _u, imp_a = _two_units_with_import(session)
    session.add(HistoricalReportRow(
        reporting_unit_id=unit_b.id, import_id=imp_a.id, source_sheet="S", source_row=1, created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_metric_cannot_reference_foreign_import(session):
    unit_a, unit_b, _u, imp_a = _two_units_with_import(session)
    session.add(HistoricalReportMetric(
        reporting_unit_id=unit_b.id, import_id=imp_a.id, metric_code="export_tons_reported",
        value_class="REPORTED_TOTAL", value_state="PRESENT", numeric_value=1.0,
        mapping_version="v1", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_metric_cannot_reference_foreign_row(session):
    unit_a, unit_b, user_a, imp_a = _two_units_with_import(session)
    row_a = HistoricalReportRow(
        reporting_unit_id=unit_a.id, import_id=imp_a.id, source_sheet="S", source_row=1, created_at=now_iso(),
    )
    session.add(row_a)
    session.commit()
    session.refresh(row_a)
    user_b = _user(session)
    imp_b = _import(session, unit_b.id, user_b.id, checksum=f"b-{_uid()}")
    session.add(HistoricalReportMetric(
        reporting_unit_id=unit_b.id, import_id=imp_b.id, row_id=row_a.id,
        metric_code="export_tons_reported", value_class="REPORTED_TOTAL",
        value_state="PRESENT", numeric_value=1.0, mapping_version="v1", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_port_call_cannot_reference_foreign_import(session):
    unit_a, unit_b, _u, imp_a = _two_units_with_import(session)
    session.add(HistoricalPortCall(
        reporting_unit_id=unit_b.id, import_id=imp_a.id, source_sheet="S", source_row=1,
        mapping_version="v1", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_cargo_cannot_reference_foreign_call(session):
    unit_a, unit_b, user_a, imp_a = _two_units_with_import(session)
    call_a = HistoricalPortCall(
        reporting_unit_id=unit_a.id, import_id=imp_a.id, source_sheet="S", source_row=1,
        mapping_version="v1", created_at=now_iso(),
    )
    session.add(call_a)
    session.commit()
    session.refresh(call_a)
    user_b = _user(session)
    imp_b = _import(session, unit_b.id, user_b.id, checksum=f"b-{_uid()}")
    session.add(HistoricalCargoRow(
        reporting_unit_id=unit_b.id, import_id=imp_b.id, source_sheet="S", source_row=1,
        port_call_id=call_a.id, transform_version="v1", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_vessel_link_cannot_reference_foreign_import(session):
    unit_a, unit_b, _u, imp_a = _two_units_with_import(session)
    session.add(HistoricalVesselLink(
        reporting_unit_id=unit_b.id, import_id=imp_a.id, created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tenant_isolation_revision_cannot_cross_units(session):
    unit_a, unit_b, user_a, imp_a = _two_units_with_import(session)
    user_b = _user(session)
    imp_b = _import(session, unit_b.id, user_b.id, checksum=f"b-{_uid()}")
    imp_a.superseded_by_import_id = imp_b.id
    with pytest.raises(IntegrityError):
        session.commit()


def test_revision_lineage_within_one_unit_is_allowed(session):
    unit = _unit(session)
    user = _user(session)
    original = _import(session, unit.id, user.id, checksum=f"rev1-{_uid()}", revision_no=1)
    replacement = _import(session, unit.id, user.id, checksum=f"rev2-{_uid()}", revision_no=2)
    original.superseded_by_import_id = replacement.id
    original.status = "SUPERSEDED"
    session.commit()
    session.refresh(original)
    assert original.superseded_by_import_id == replacement.id


def test_vessel_link_requires_import(session):
    unit = _unit(session)
    session.add(HistoricalVesselLink(
        reporting_unit_id=unit.id, import_id=None, raw_vessel_name="X", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


# ── Fail-closed import-actor authorization (PLATFORM_ADMIN / PORT_STAFF) ──────

def test_import_actor_portstaff_with_membership_allowed(session):
    unit = _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit.id, staff.id)
    validate_import_actor(session, reporting_unit_id=unit.id, user=staff)  # no raise


def test_import_actor_portstaff_on_foreign_unit_rejected(session):
    unit_a, unit_b = _unit(session), _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit_a.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit_b.id, user=staff)


def test_import_actor_portstaff_cannot_cross_ports_with_platform_context(session):
    """A platform context never lets PORT_STAFF cross into a unit they do not
    belong to."""
    unit_a, unit_b = _unit(session), _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit_a.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit_b.id, user=staff, platform_context=True)


def test_import_actor_portstaff_multi_port_membership_operates_either(session):
    """One PORT_STAFF may hold memberships in multiple ports and explicitly act
    in either."""
    unit_a, unit_b = _unit(session), _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit_a.id, staff.id)
    _add_user_membership(session, unit_b.id, staff.id)
    validate_import_actor(session, reporting_unit_id=unit_a.id, user=staff)
    validate_import_actor(session, reporting_unit_id=unit_b.id, user=staff)


def test_import_actor_platform_admin_with_context_allowed(session):
    """A PLATFORM_ADMIN with explicit context may operate an active unit;
    membership is neither required nor consulted."""
    unit = _unit(session)
    platform_admin = _user(session, "PLATFORM_ADMIN")
    validate_import_actor(session, reporting_unit_id=unit.id, user=platform_admin, platform_context=True)


def test_import_actor_platform_admin_without_context_rejected(session):
    unit = _unit(session)
    platform_admin = _user(session, "PLATFORM_ADMIN")
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=platform_admin)


def test_import_actor_platform_admin_membership_is_not_sufficient(session):
    """Even a PLATFORM_ADMIN holding a membership still needs explicit context —
    membership is neither required nor sufficient for the platform role."""
    unit = _unit(session)
    platform_admin = _user(session, "PLATFORM_ADMIN")
    _add_user_membership(session, unit.id, platform_admin.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=platform_admin)


def test_import_actor_legacy_admin_role_rejected(session):
    """A leftover legacy 'ADMIN' role is not a valid product role and is refused."""
    unit = _unit(session)
    legacy = _user(session, "ADMIN")
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=legacy, platform_context=True)


def test_import_actor_customer_rejected(session):
    unit = _unit(session)
    customer = _user(session, "CUSTOMER")
    _add_user_membership(session, unit.id, customer.id)  # even with a row, CUSTOMER is refused
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=customer)


def test_import_actor_inactive_user_rejected(session):
    unit = _unit(session)
    staff = _user(session, "PORT_STAFF", is_active=0)
    _add_user_membership(session, unit.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=staff)


def test_import_actor_missing_reporting_unit_rejected(session):
    staff = _user(session, "PORT_STAFF")
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=999999, user=staff)


def test_import_actor_missing_user_rejected(session):
    unit = _unit(session)
    with pytest.raises(HistoricalAuthorizationError):
        validate_import_actor(session, reporting_unit_id=unit.id, user=None)


def test_import_actor_on_inactive_unit_rejected(session):
    unit = _unit(session, is_active=0)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError) as excinfo:
        validate_import_actor(session, reporting_unit_id=unit.id, user=staff)
    assert "not active" in str(excinfo.value)


def test_platform_admin_cannot_override_inactive_unit(session):
    """A PLATFORM_ADMIN with explicit context still cannot act on an inactive
    unit — the active-unit gate runs before role authorization."""
    unit = _unit(session, is_active=0)
    platform_admin = _user(session, "PLATFORM_ADMIN")
    with pytest.raises(HistoricalAuthorizationError) as excinfo:
        validate_import_actor(session, reporting_unit_id=unit.id, user=platform_admin, platform_context=True)
    assert "not active" in str(excinfo.value)


# ── Fail-closed reviewer authorization ───────────────────────────────────────

def test_reviewer_with_membership_allowed(session):
    unit = _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit.id, staff.id)
    validate_reviewer(session, reporting_unit_id=unit.id, reviewer=staff)  # no raise


def test_reviewer_platform_admin_with_context_allowed(session):
    unit = _unit(session)
    platform_admin = _user(session, "PLATFORM_ADMIN")
    validate_reviewer(session, reporting_unit_id=unit.id, reviewer=platform_admin, platform_context=True)


def test_reviewer_cross_port_rejected(session):
    unit_a, unit_b = _unit(session), _unit(session)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit_a.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_reviewer(session, reporting_unit_id=unit_b.id, reviewer=staff)


def test_reviewer_customer_rejected(session):
    unit = _unit(session)
    customer = _user(session, "CUSTOMER")
    _add_user_membership(session, unit.id, customer.id)
    with pytest.raises(HistoricalAuthorizationError):
        validate_reviewer(session, reporting_unit_id=unit.id, reviewer=customer)


def test_reviewer_on_inactive_unit_rejected(session):
    unit = _unit(session, is_active=0)
    staff = _user(session, "PORT_STAFF")
    _add_user_membership(session, unit.id, staff.id)
    with pytest.raises(HistoricalAuthorizationError) as excinfo:
        validate_reviewer(session, reporting_unit_id=unit.id, reviewer=staff)
    assert "not active" in str(excinfo.value)


# ── Candidate-vessel membership validation ───────────────────────────────────

def test_vessel_link_same_unit_membership_allowed(session):
    unit = _unit(session)
    org = _org(session)
    _add_org_membership(session, unit.id, org.id)
    vessel = _vessel(session, org.id)
    validate_vessel_link_tenant(session, reporting_unit_id=unit.id, candidate_vessel_id=vessel.id)
    # Unresolved candidate is always allowed.
    validate_vessel_link_tenant(session, reporting_unit_id=unit.id, candidate_vessel_id=None)


def test_vessel_link_other_port_only_membership_rejected(session):
    unit_a, unit_b = _unit(session), _unit(session)
    org = _org(session)
    _add_org_membership(session, unit_a.id, org.id)  # only Port A
    vessel = _vessel(session, org.id)
    with pytest.raises(HistoricalTenantError):
        validate_vessel_link_tenant(session, reporting_unit_id=unit_b.id, candidate_vessel_id=vessel.id)


def test_vessel_link_multi_port_membership_allowed_in_each(session):
    unit_a, unit_b = _unit(session), _unit(session)
    org = _org(session)
    _add_org_membership(session, unit_a.id, org.id)
    _add_org_membership(session, unit_b.id, org.id)
    vessel = _vessel(session, org.id)
    validate_vessel_link_tenant(session, reporting_unit_id=unit_a.id, candidate_vessel_id=vessel.id)
    validate_vessel_link_tenant(session, reporting_unit_id=unit_b.id, candidate_vessel_id=vessel.id)


def test_vessel_link_missing_vessel_rejected(session):
    unit = _unit(session)
    with pytest.raises(HistoricalTenantError):
        validate_vessel_link_tenant(session, reporting_unit_id=unit.id, candidate_vessel_id=999999)


def test_vessel_link_unbound_vessel_rejected(session):
    unit = _unit(session)
    vessel = Vessel(
        organization_id=None, name="Orphan", registration_no=f"REG-{_uid()}",
        vessel_type="Sa lan", vessel_class="VR-SI", created_at=now_iso(), updated_at=now_iso(),
    )
    session.add(vessel)
    session.commit()
    session.refresh(vessel)
    with pytest.raises(HistoricalTenantError):
        validate_vessel_link_tenant(session, reporting_unit_id=unit.id, candidate_vessel_id=vessel.id)


# ── Tenant-scoped audit ──────────────────────────────────────────────────────

def test_audit_without_reporting_unit_still_works(session):
    """Existing non-historical audit remains valid with a NULL reporting unit."""
    audit(session, "auth", 0, "LOGIN_FAILURE", "bad password")
    session.commit()
    event = session.query(AuditEvent).filter_by(entity_type="auth", action="LOGIN_FAILURE").one()
    assert event.reporting_unit_id is None


def test_audit_stores_reporting_unit_without_org_conflation(session):
    """Historical audit records the Port in reporting_unit_id, never in organization_id."""
    unit = _unit(session)
    user = _user(session)
    _add_user_membership(session, unit.id, user.id)
    imp = _import(session, unit.id, user.id, checksum=f"aud-{_uid()}")
    audit(
        session, "historical_report_import", imp.id, "IMPORT_COMMITTED",
        "Historical TOS import committed", actor_user_id=user.id, reporting_unit_id=unit.id,
    )
    session.commit()
    event = (
        session.query(AuditEvent)
        .filter_by(entity_type="historical_report_import", entity_id=imp.id)
        .one()
    )
    assert event.reporting_unit_id == unit.id
    assert event.organization_id is None  # Port id is never written into the customer-org column
    assert event.actor_user_id == user.id


def test_audit_with_nonexistent_reporting_unit_rejected(session):
    session.add(AuditEvent(
        entity_type="historical_report_import", entity_id=1, action="X", summary="y",
        reporting_unit_id=999999, correlation_id="", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


# ── Database-level cascade via direct SQL deletion (retained) ────────────────

def test_database_cascade_delete_via_direct_sql(session):
    unit = _unit(session)
    user = _user(session)
    imp = _import(session, unit.id, user.id, checksum=f"cas-{_uid()}")
    call = HistoricalPortCall(
        reporting_unit_id=unit.id, import_id=imp.id, source_sheet="S", source_row=1,
        mapping_version="v1", created_at=now_iso(),
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    row = HistoricalReportRow(
        reporting_unit_id=unit.id, import_id=imp.id, source_sheet="S", source_row=2, created_at=now_iso(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    session.add_all([
        HistoricalReportMetric(
            reporting_unit_id=unit.id, import_id=imp.id, row_id=row.id,
            metric_code="export_tons_reported", value_class="REPORTED_TOTAL",
            value_state="PRESENT", numeric_value=1.0, mapping_version="v1", created_at=now_iso(),
        ),
        HistoricalCargoRow(
            reporting_unit_id=unit.id, import_id=imp.id, source_sheet="S", source_row=3,
            port_call_id=call.id, transform_version="v1", created_at=now_iso(),
        ),
        HistoricalVesselLink(
            reporting_unit_id=unit.id, import_id=imp.id, port_call_id=call.id,
            raw_vessel_name="X", created_at=now_iso(),
        ),
    ])
    session.commit()
    import_id = imp.id
    session.close()

    with _engine.begin() as conn:
        conn.execute(text("DELETE FROM historical_report_imports WHERE id=:i"), {"i": import_id})
    with _engine.connect() as conn:
        for table in ("historical_report_rows", "historical_report_metrics",
                      "historical_port_calls", "historical_cargo_rows", "historical_vessel_links"):
            remaining = conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE import_id=:i"), {"i": import_id}
            ).scalar()
            assert remaining == 0, f"{table} rows survived a cascade delete"


# ── Blank / zero / invalid remain distinct (retained) ────────────────────────

def test_blank_zero_and_invalid_states_are_distinct(session):
    unit = _unit(session)
    user = _user(session)
    imp = _import(session, unit.id, user.id, checksum=f"states-{_uid()}",
                  source_kind="reported_pl03", mapping_version="pl03_v1")
    blank = HistoricalReportMetric(
        reporting_unit_id=unit.id, import_id=imp.id, metric_code="import_tons_reported",
        value_class="REPORTED_TOTAL", numeric_value=None, value_state="BLANK",
        source_cell="BAO CAO!L10", mapping_version="pl03_v1", created_at=now_iso(),
    )
    measured_zero = HistoricalReportMetric(
        reporting_unit_id=unit.id, import_id=imp.id, metric_code="export_tons_reported",
        value_class="REPORTED_TOTAL", numeric_value=0.0, value_state="ZERO",
        source_cell="BAO CAO!I10", mapping_version="pl03_v1", created_at=now_iso(),
    )
    session.add_all([blank, measured_zero])
    session.commit()
    call = HistoricalPortCall(
        reporting_unit_id=unit.id, import_id=imp.id, source_sheet="S", source_row=1,
        mapping_version="pl03_v1", created_at=now_iso(),
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    invalid = HistoricalCargoRow(
        reporting_unit_id=unit.id, import_id=imp.id, source_sheet="S", source_row=2,
        port_call_id=call.id, weight_raw="n/a", weight_tonnes=None, weight_state="INVALID",
        transform_version="v1", created_at=now_iso(),
    )
    session.add(invalid)
    session.commit()
    session.refresh(blank)
    session.refresh(measured_zero)
    session.refresh(invalid)
    assert blank.value_state == "BLANK" and blank.numeric_value is None
    assert measured_zero.value_state == "ZERO" and measured_zero.numeric_value == 0.0
    assert invalid.weight_state == "INVALID" and invalid.weight_raw == "n/a"


def test_blank_metric_with_a_number_is_rejected(session):
    unit = _unit(session)
    user = _user(session)
    imp = _import(session, unit.id, user.id, checksum=f"badstate-{_uid()}",
                  source_kind="reported_pl03", mapping_version="pl03_v1")
    session.add(HistoricalReportMetric(
        reporting_unit_id=unit.id, import_id=imp.id, metric_code="export_tons_reported",
        value_class="REPORTED_TOTAL", numeric_value=5.0, value_state="BLANK",
        mapping_version="pl03_v1", created_at=now_iso(),
    ))
    with pytest.raises(IntegrityError):
        session.commit()


# ── ATB / ATD kept distinct, no ATA field (retained) ─────────────────────────

def test_atb_and_atd_are_distinct_and_no_ata_field():
    columns = {c.name for c in HistoricalPortCall.__table__.columns}
    assert {"actual_berthing_at_raw", "actual_berthing_at",
            "actual_departure_at_raw", "actual_departure_at"}.issubset(columns)
    assert not any("ata" in name.lower() or name.startswith("actual_arrival") for name in columns)


def test_port_call_stores_atb_and_atd_separately(session):
    unit = _unit(session)
    user = _user(session)
    imp = _import(session, unit.id, user.id, checksum=f"time-{_uid()}")
    call = HistoricalPortCall(
        reporting_unit_id=unit.id, import_id=imp.id, source_sheet="Sheet1", source_row=2,
        mapping_version="tos_berth_v1",
        actual_berthing_at_raw="07/07/2026 08:30:00", actual_berthing_at="2026-07-07T08:30:00",
        actual_departure_at_raw="09/07/2026 11:00:00", actual_departure_at="2026-07-09T11:00:00",
        reporting_month="2026-07", created_at=now_iso(),
    )
    session.add(call)
    session.commit()
    session.refresh(call)
    assert call.actual_berthing_at != call.actual_departure_at
    assert call.reporting_month == "2026-07"
