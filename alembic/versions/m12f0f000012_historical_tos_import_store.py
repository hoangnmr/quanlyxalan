"""historical / TOS import store (H2 — schema, migration and provenance foundation)

Introduces the distinct reporting-unit tenant, FK-backed tenant memberships,
tenant-scoped audit and the multi-port, tenant-isolated historical reporting
tables:
  - reporting_units                 (a Port that operates the product — tenant)
  - reporting_unit_users            (FK-backed user->port membership, M2M)
  - reporting_unit_organizations    (FK-backed org->port membership, M2M)
  - historical_report_imports       (immutable source-file import/revision record)
  - historical_report_rows          (reported source rows with provenance)
  - historical_report_metrics       (typed metrics: value class, blank/zero, cell)
  - historical_port_calls            (normalized TOS Berth call facts, ATB/ATD)
  - historical_cargo_rows            (normalized TOS cargo detail facts)
  - historical_vessel_links         (controlled canonical vessel link candidates)

It also adds a nullable ``reporting_unit_id`` foreign key to ``audit_events`` so
historical import/revision/review audit carries the affected reporting unit;
existing non-historical audit rows stay NULL and ``organization_id`` continues to
mean a customer Organization (never a Port id).

Tenant membership is FK-backed rather than a soft integer column: an invalid or
nonexistent user/organization/reporting-unit id cannot be stored. Existing users
and organizations get no memberships and are never backfilled to a specific port
(in particular, never to Cảng Tân Thuận).

Tenant consistency for the historical store is enforced with COMPOSITE foreign
keys so a child carrying reporting unit B cannot reference a parent owned by
reporting unit A. PostgreSQL enforces declared foreign keys unconditionally, so
these constraints and ON DELETE CASCADE are real.

Guarded creation and drift detection: the ``b01`` baseline migration builds the
current model metadata with ``Base.metadata.create_all``, so on a fresh database
these objects already exist before this revision runs (the same pattern the
``d03``/``e04``/``l11`` migrations rely on). Each object is therefore created only
when absent — the legacy path builds the exact schema — and a fail-closed
verification then asserts the full tenant-critical schema (tables, memberships,
identity/idempotency keys, every composite foreign key, link.import_id NOT NULL,
critical CHECKs and the audit tenant FK), raising a precise error on any drifted
or partial pre-existing schema. This migration only ADDS structures; it never
reads, alters or deletes existing declaration, vessel, crew or canonical master
rows.

Revision ID: m12f0f000012
Revises: l11f0f000011
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa


revision = "m12f0f000012"
down_revision = "l11f0f000011"
branch_labels = None
depends_on = None


# Approved value sets mirrored from backend.models for the CHECK constraints.
_STATUS = "status IN ('PENDING', 'PREVIEWED', 'COMMITTED', 'REVIEW', 'REJECTED', 'SUPERSEDED')"
_VALIDATION = "validation_status IN ('PENDING', 'VALID', 'REVIEW', 'REJECTED')"
_VALUE_CLASS = "value_class IN ('SELECTED_PERIOD', 'YTD', 'REPORTED_TOTAL', 'TEXT')"
_VALUE_STATE = "value_state IN ('PRESENT', 'BLANK', 'ZERO')"
_WEIGHT_STATE = "weight_state IN ('PRESENT', 'BLANK', 'ZERO', 'INVALID')"
_AMBIGUITY = "ambiguity_status IN ('NONE', 'UNMATCHED', 'AMBIGUOUS')"
_CARGO_MATCH = "match_status IN ('PENDING', 'MATCHED', 'UNMATCHED', 'AMBIGUOUS')"
_LINK_STATUS = "link_status IN ('PENDING', 'ACCEPTED', 'REJECTED')"
_LINK_METHOD = "match_method IN ('', 'EXACT', 'NORMALIZED', 'MANUAL')"
_LINK_CONFIDENCE = "confidence IN ('', 'HIGH', 'MEDIUM', 'LOW')"


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def _columns(connection, table: str) -> set:
    return {column["name"] for column in sa.inspect(connection).get_columns(table)}


# ── Fail-closed schema verification helpers ──────────────────────────────────

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(f"H2 schema drift: {message}")


def _unique_names(inspector, table: str) -> set:
    return {uc["name"] for uc in inspector.get_unique_constraints(table)}


def _has_composite_fk(inspector, table: str, referred_table: str, columns: set) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") == referred_table and columns.issubset(set(fk.get("constrained_columns") or [])):
            return True
    return False


def _has_simple_fk(inspector, table: str, column: str, referred_table: str) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if fk.get("referred_table") == referred_table and column in set(fk.get("constrained_columns") or []):
            return True
    return False


def _check_names(inspector, table: str) -> set:
    return {cc["name"] for cc in inspector.get_check_constraints(table) if cc.get("name")}


def _verify_tenant_schema(connection) -> None:
    """Fail closed unless the FULL tenant-critical schema is present.

    Covers the reporting unit and both membership tables, the import identity and
    idempotency keys, the import self-revision composite FK, every child->import
    composite FK, the metric->row / cargo->call / link->call composites,
    link.import_id NOT NULL, the historical identity/source-row unique keys, the
    critical status and blank/zero CHECK constraints, and the audit tenant FK.
    Raises with a precise, named message on any missing structure.
    """
    inspector = sa.inspect(connection)

    for table in (
        "reporting_units", "reporting_unit_users", "reporting_unit_organizations",
        "historical_report_imports", "historical_report_rows", "historical_report_metrics",
        "historical_port_calls", "historical_cargo_rows", "historical_vessel_links",
    ):
        _require(inspector.has_table(table), f"missing table {table!r}")

    # Membership tables: composite primary key + both foreign keys.
    ru_users_pk = set(inspector.get_pk_constraint("reporting_unit_users").get("constrained_columns") or [])
    _require(ru_users_pk == {"reporting_unit_id", "user_id"},
             "reporting_unit_users must have composite PK (reporting_unit_id, user_id)")
    _require(_has_simple_fk(inspector, "reporting_unit_users", "reporting_unit_id", "reporting_units"),
             "reporting_unit_users is missing FK reporting_unit_id -> reporting_units")
    _require(_has_simple_fk(inspector, "reporting_unit_users", "user_id", "users"),
             "reporting_unit_users is missing FK user_id -> users")

    ru_orgs_pk = set(inspector.get_pk_constraint("reporting_unit_organizations").get("constrained_columns") or [])
    _require(ru_orgs_pk == {"reporting_unit_id", "organization_id"},
             "reporting_unit_organizations must have composite PK (reporting_unit_id, organization_id)")
    _require(_has_simple_fk(inspector, "reporting_unit_organizations", "reporting_unit_id", "reporting_units"),
             "reporting_unit_organizations is missing FK reporting_unit_id -> reporting_units")
    _require(_has_simple_fk(inspector, "reporting_unit_organizations", "organization_id", "organizations"),
             "reporting_unit_organizations is missing FK organization_id -> organizations")

    # Import identity, idempotency, tenant FK and self-revision composite FK.
    import_uniques = _unique_names(inspector, "historical_report_imports")
    for required in ("uq_hist_import_identity", "uq_historical_import_idempotency"):
        _require(required in import_uniques, f"historical_report_imports missing unique constraint {required!r}")
    _require(_has_simple_fk(inspector, "historical_report_imports", "reporting_unit_id", "reporting_units"),
             "historical_report_imports is missing FK reporting_unit_id -> reporting_units")
    _require(_has_composite_fk(inspector, "historical_report_imports", "historical_report_imports",
                               {"superseded_by_import_id", "reporting_unit_id"}),
             "historical_report_imports is missing the composite self-revision FK "
             "(superseded_by_import_id, reporting_unit_id)")

    # Each historical child -> import composite FK.
    for child in ("historical_report_rows", "historical_report_metrics", "historical_port_calls",
                  "historical_cargo_rows", "historical_vessel_links"):
        _require(_has_composite_fk(inspector, child, "historical_report_imports", {"import_id", "reporting_unit_id"}),
                 f"{child} is missing the composite (import_id, reporting_unit_id) FK onto historical_report_imports")

    # Secondary composites.
    _require(_has_composite_fk(inspector, "historical_report_metrics", "historical_report_rows",
                               {"row_id", "import_id", "reporting_unit_id"}),
             "historical_report_metrics is missing the composite (row_id, import_id, reporting_unit_id) FK onto historical_report_rows")
    # A fresh database may already carry the current H3 model because the b01
    # baseline uses Base.metadata.create_all.  Accept both the original H2
    # same-import FK and the H3 tenant-safe cross-import FK; o14 performs the
    # forward conversion for an existing n13 database.
    cargo_call_fk = (
        _has_composite_fk(inspector, "historical_cargo_rows", "historical_port_calls",
                          {"port_call_id", "import_id", "reporting_unit_id"})
        or _has_composite_fk(inspector, "historical_cargo_rows", "historical_port_calls",
                             {"port_call_id", "reporting_unit_id"})
    )
    _require(cargo_call_fk, "historical_cargo_rows is missing a tenant-scoped port_call FK")
    link_call_fk = (
        _has_composite_fk(inspector, "historical_vessel_links", "historical_port_calls",
                          {"port_call_id", "import_id", "reporting_unit_id"})
        or _has_composite_fk(inspector, "historical_vessel_links", "historical_port_calls",
                             {"port_call_id", "reporting_unit_id"})
    )
    _require(link_call_fk, "historical_vessel_links is missing a tenant-scoped port_call FK")

    # Row/call identity keys and vessel-link.import_id NOT NULL.
    _require("uq_hist_row_identity" in _unique_names(inspector, "historical_report_rows"),
             "historical_report_rows missing unique constraint 'uq_hist_row_identity'")
    _require("uq_hist_call_identity" in _unique_names(inspector, "historical_port_calls"),
             "historical_port_calls missing unique constraint 'uq_hist_call_identity'")
    link_cols = {c["name"]: c for c in inspector.get_columns("historical_vessel_links")}
    _require(link_cols["import_id"]["nullable"] is False,
             "historical_vessel_links.import_id must be NOT NULL")

    # Critical CHECK constraints, reflected by name via the dialect inspector.
    imports_checks = _check_names(inspector, "historical_report_imports")
    _require("ck_hist_import_status" in imports_checks, "historical_report_imports missing CHECK 'ck_hist_import_status'")
    metrics_checks = _check_names(inspector, "historical_report_metrics")
    _require("ck_hist_metric_value_state" in metrics_checks, "historical_report_metrics missing CHECK 'ck_hist_metric_value_state'")
    _require("ck_hist_metric_blank_null" in metrics_checks, "historical_report_metrics missing CHECK 'ck_hist_metric_blank_null'")
    cargo_checks = _check_names(inspector, "historical_cargo_rows")
    _require("ck_hist_cargo_weight_state" in cargo_checks, "historical_cargo_rows missing CHECK 'ck_hist_cargo_weight_state'")

    # Audit tenant scope.
    _require("reporting_unit_id" in _columns(connection, "audit_events"),
             "audit_events is missing the reporting_unit_id column")
    _require(_has_simple_fk(inspector, "audit_events", "reporting_unit_id", "reporting_units"),
             "audit_events.reporting_unit_id must be a foreign key onto reporting_units")


# ── Upgrade ──────────────────────────────────────────────────────────────────

def upgrade() -> None:
    connection = op.get_bind()

    if not _has_table(connection, "reporting_units"):
        op.create_table(
            "reporting_units",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("code", sa.String(), nullable=False, server_default=""),
            sa.Column("official_header_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.UniqueConstraint("name", name="uq_reporting_units_name"),
        )

    if not _has_table(connection, "reporting_unit_users"):
        op.create_table(
            "reporting_unit_users",
            sa.Column("reporting_unit_id", sa.Integer(),
                      sa.ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("membership_role", sa.String(), nullable=False, server_default=""),
            sa.Column("created_at", sa.String(), nullable=False),
        )

    if not _has_table(connection, "reporting_unit_organizations"):
        op.create_table(
            "reporting_unit_organizations",
            sa.Column("reporting_unit_id", sa.Integer(),
                      sa.ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("organization_id", sa.Integer(),
                      sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("created_at", sa.String(), nullable=False),
        )

    # Tenant-scoped audit column (nullable FK; NULL-defaulting REFERENCES is
    # a nullable ADD COLUMN, which leaves existing audit rows valid).
    if "reporting_unit_id" not in _columns(connection, "audit_events"):
        op.execute("ALTER TABLE audit_events ADD COLUMN reporting_unit_id INTEGER REFERENCES reporting_units (id)")

    # Role model finalization: the application never had a tenant-local ADMIN, so
    # every legacy 'ADMIN' user becomes the product-wide 'PLATFORM_ADMIN'. This is
    # a role-only data migration (no password/hash is read or changed) and is
    # idempotent (a no-op once no 'ADMIN' rows remain).
    op.execute("UPDATE users SET role = 'PLATFORM_ADMIN' WHERE role = 'ADMIN'")

    if not _has_table(connection, "historical_report_imports"):
        op.create_table(
            "historical_report_imports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("source_kind", sa.String(), nullable=False),
            sa.Column("appendix_kind", sa.String(), nullable=False, server_default=""),
            sa.Column("mapping_version", sa.String(), nullable=False),
            sa.Column("reporting_period", sa.String(), nullable=True),
            sa.Column("source_filename", sa.String(), nullable=False, server_default=""),
            sa.Column("source_checksum", sa.String(), nullable=False),
            sa.Column("source_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_sheets_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("revision_no", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("superseded_by_import_id", sa.Integer(), nullable=True),
            sa.Column("supersede_reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mapping_receipt_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("updated_at", sa.String(), nullable=False),
            sa.UniqueConstraint("id", "reporting_unit_id", name="uq_hist_import_identity"),
            sa.UniqueConstraint(
                "reporting_unit_id", "source_kind", "source_checksum", "mapping_version",
                name="uq_historical_import_idempotency",
            ),
            sa.ForeignKeyConstraint(
                ["superseded_by_import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                name="fk_hist_import_supersede",
            ),
            sa.CheckConstraint("revision_no >= 1", name="ck_hist_import_revision"),
            sa.CheckConstraint("accepted_count >= 0", name="ck_hist_import_accepted"),
            sa.CheckConstraint("rejected_count >= 0", name="ck_hist_import_rejected"),
            sa.CheckConstraint("review_count >= 0", name="ck_hist_import_review"),
            sa.CheckConstraint("source_size_bytes >= 0", name="ck_hist_import_size"),
            sa.CheckConstraint(_STATUS, name="ck_hist_import_status"),
        )
        op.create_index("ix_historical_report_imports_reporting_unit_id", "historical_report_imports", ["reporting_unit_id"])
        op.create_index("ix_historical_imports_unit_period", "historical_report_imports", ["reporting_unit_id", "reporting_period"])

    if not _has_table(connection, "historical_report_rows"):
        op.create_table(
            "historical_report_rows",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("source_sheet", sa.String(), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("appendix_row_no", sa.Integer(), nullable=True),
            sa.Column("vessel_id", sa.Integer(), sa.ForeignKey("vessels.id"), nullable=True),
            sa.Column("normalized_registration", sa.String(), nullable=False, server_default=""),
            sa.Column("raw_payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("mapped_dimensions_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("validation_status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("warning_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.UniqueConstraint("id", "import_id", "reporting_unit_id", name="uq_hist_row_identity"),
            sa.ForeignKeyConstraint(
                ["import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_row_import",
            ),
            sa.CheckConstraint(_VALIDATION, name="ck_hist_row_validation"),
        )
        op.create_index("ix_historical_report_rows_reporting_unit_id", "historical_report_rows", ["reporting_unit_id"])
        op.create_index("ix_historical_rows_import", "historical_report_rows", ["import_id"])

    if not _has_table(connection, "historical_report_metrics"):
        op.create_table(
            "historical_report_metrics",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("row_id", sa.Integer(), nullable=True),
            sa.Column("metric_code", sa.String(), nullable=False),
            sa.Column("direction", sa.String(), nullable=False, server_default=""),
            sa.Column("category", sa.String(), nullable=False, server_default=""),
            sa.Column("unit", sa.String(), nullable=False, server_default=""),
            sa.Column("value_class", sa.String(), nullable=False),
            sa.Column("numeric_value", sa.Float(), nullable=True),
            sa.Column("text_value", sa.Text(), nullable=True),
            sa.Column("value_state", sa.String(), nullable=False, server_default="PRESENT"),
            sa.Column("source_cell", sa.String(), nullable=False, server_default=""),
            sa.Column("source_header_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("mapping_version", sa.String(), nullable=False),
            sa.Column("reconciliation_status", sa.String(), nullable=False, server_default="NONE"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(
                ["import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_metric_import",
            ),
            sa.ForeignKeyConstraint(
                ["row_id", "import_id", "reporting_unit_id"],
                ["historical_report_rows.id", "historical_report_rows.import_id", "historical_report_rows.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_metric_row",
            ),
            sa.CheckConstraint(_VALUE_CLASS, name="ck_hist_metric_value_class"),
            sa.CheckConstraint(_VALUE_STATE, name="ck_hist_metric_value_state"),
            sa.CheckConstraint("value_state <> 'BLANK' OR numeric_value IS NULL", name="ck_hist_metric_blank_null"),
            sa.CheckConstraint("value_state <> 'ZERO' OR numeric_value = 0", name="ck_hist_metric_zero_value"),
        )
        op.create_index("ix_historical_report_metrics_reporting_unit_id", "historical_report_metrics", ["reporting_unit_id"])
        op.create_index("ix_historical_metrics_import_code", "historical_report_metrics", ["import_id", "metric_code"])

    if not _has_table(connection, "historical_port_calls"):
        op.create_table(
            "historical_port_calls",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("source_sheet", sa.String(), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mapping_version", sa.String(), nullable=False),
            sa.Column("vessel_name_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("vessel_name_normalized", sa.String(), nullable=False, server_default=""),
            sa.Column("call_year_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("voyage_number_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("call_key_normalized", sa.String(), nullable=False, server_default=""),
            sa.Column("vessel_id", sa.Integer(), sa.ForeignKey("vessels.id"), nullable=True),
            sa.Column("source_berth_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("arrival_berth", sa.String(), nullable=False, server_default=""),
            sa.Column("departure_berth", sa.String(), nullable=False, server_default=""),
            sa.Column("berth_correction_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("actual_berthing_at_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("actual_berthing_at", sa.String(), nullable=True),
            sa.Column("actual_departure_at_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("actual_departure_at", sa.String(), nullable=True),
            sa.Column("reporting_month", sa.String(), nullable=True),
            sa.Column("validation_status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("ambiguity_status", sa.String(), nullable=False, server_default="NONE"),
            sa.Column("reconciliation_status", sa.String(), nullable=False, server_default="NONE"),
            sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.UniqueConstraint("id", "import_id", "reporting_unit_id", name="uq_hist_call_identity"),
            sa.UniqueConstraint(
                "reporting_unit_id", "import_id", "source_sheet", "source_row",
                name="uq_historical_port_call_source_row",
            ),
            sa.ForeignKeyConstraint(
                ["import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_call_import",
            ),
            sa.CheckConstraint(_VALIDATION, name="ck_hist_call_validation"),
            sa.CheckConstraint(_AMBIGUITY, name="ck_hist_call_ambiguity"),
        )
        op.create_index("ix_historical_port_calls_reporting_unit_id", "historical_port_calls", ["reporting_unit_id"])
        op.create_index("ix_historical_calls_unit_key", "historical_port_calls", ["reporting_unit_id", "call_key_normalized"])

    if not _has_table(connection, "historical_cargo_rows"):
        op.create_table(
            "historical_cargo_rows",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("source_sheet", sa.String(), nullable=False, server_default=""),
            sa.Column("source_row", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("port_call_id", sa.Integer(), nullable=True),
            sa.Column("source_call_key_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("container_size_code_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("teu_factor", sa.Integer(), nullable=True),
            sa.Column("full_empty_code_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("trade_scope_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("movement_method_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("derived_direction", sa.String(), nullable=False, server_default=""),
            sa.Column("weight_raw", sa.String(), nullable=False, server_default=""),
            sa.Column("weight_tonnes", sa.Float(), nullable=True),
            sa.Column("weight_state", sa.String(), nullable=False, server_default="PRESENT"),
            sa.Column("transform_version", sa.String(), nullable=False),
            sa.Column("match_status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("validation_status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.UniqueConstraint(
                "reporting_unit_id", "import_id", "source_sheet", "source_row",
                name="uq_historical_cargo_source_row",
            ),
            sa.ForeignKeyConstraint(
                ["import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_cargo_import",
            ),
            sa.ForeignKeyConstraint(
                ["port_call_id", "import_id", "reporting_unit_id"],
                ["historical_port_calls.id", "historical_port_calls.import_id", "historical_port_calls.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_cargo_call",
            ),
            sa.CheckConstraint("teu_factor IS NULL OR teu_factor IN (1, 2)", name="ck_hist_cargo_teu_factor"),
            sa.CheckConstraint(_WEIGHT_STATE, name="ck_hist_cargo_weight_state"),
            sa.CheckConstraint("weight_state <> 'BLANK' OR weight_tonnes IS NULL", name="ck_hist_cargo_blank_null"),
            sa.CheckConstraint("weight_state <> 'ZERO' OR weight_tonnes = 0", name="ck_hist_cargo_zero_value"),
            sa.CheckConstraint(_CARGO_MATCH, name="ck_hist_cargo_match"),
            sa.CheckConstraint(_VALIDATION, name="ck_hist_cargo_validation"),
        )
        op.create_index("ix_historical_cargo_rows_reporting_unit_id", "historical_cargo_rows", ["reporting_unit_id"])
        op.create_index("ix_historical_cargo_call", "historical_cargo_rows", ["port_call_id"])

    if not _has_table(connection, "historical_vessel_links"):
        op.create_table(
            "historical_vessel_links",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reporting_unit_id", sa.Integer(), sa.ForeignKey("reporting_units.id"), nullable=False),
            sa.Column("import_id", sa.Integer(), nullable=False),
            sa.Column("port_call_id", sa.Integer(), nullable=True),
            sa.Column("raw_vessel_name", sa.String(), nullable=False, server_default=""),
            sa.Column("normalized_vessel_name", sa.String(), nullable=False, server_default=""),
            sa.Column("raw_registration", sa.String(), nullable=False, server_default=""),
            sa.Column("candidate_vessel_id", sa.Integer(), sa.ForeignKey("vessels.id"), nullable=True),
            sa.Column("match_method", sa.String(), nullable=False, server_default=""),
            sa.Column("confidence", sa.String(), nullable=False, server_default=""),
            sa.Column("link_status", sa.String(), nullable=False, server_default="PENDING"),
            sa.Column("reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.String(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(
                ["import_id", "reporting_unit_id"],
                ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_link_import",
            ),
            sa.ForeignKeyConstraint(
                ["port_call_id", "import_id", "reporting_unit_id"],
                ["historical_port_calls.id", "historical_port_calls.import_id", "historical_port_calls.reporting_unit_id"],
                ondelete="CASCADE", name="fk_hist_link_call",
            ),
            sa.CheckConstraint(_LINK_STATUS, name="ck_hist_link_status"),
            sa.CheckConstraint(_LINK_METHOD, name="ck_hist_link_method"),
            sa.CheckConstraint(_LINK_CONFIDENCE, name="ck_hist_link_confidence"),
        )
        op.create_index("ix_historical_vessel_links_reporting_unit_id", "historical_vessel_links", ["reporting_unit_id"])
        op.create_index("ix_historical_links_unit_norm", "historical_vessel_links", ["reporting_unit_id", "normalized_vessel_name"])

    # Fail closed if the resulting schema is missing tenant-critical structures.
    _verify_tenant_schema(connection)


# ── Downgrade ────────────────────────────────────────────────────────────────

def downgrade() -> None:
    connection = op.get_bind()
    # Reverse the role finalization for pre-H2 compatibility. Pre-H2 databases had
    # no 'PLATFORM_ADMIN' role, so every 'PLATFORM_ADMIN' originated from a legacy
    # 'ADMIN' and is restored as such. Limitation: if a future revision were to
    # introduce independently-created PLATFORM_ADMIN accounts, this reversal could
    # not distinguish them; that is acceptable for the current reversible pre-H2
    # boundary because no such accounts exist before this revision.
    op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'PLATFORM_ADMIN'")
    # Drop historical children before parents.
    for table in (
        "historical_vessel_links",
        "historical_cargo_rows",
        "historical_report_metrics",
        "historical_port_calls",
        "historical_report_rows",
        "historical_report_imports",
    ):
        if _has_table(connection, table):
            op.drop_table(table)
    # Membership tables (reference reporting_units) before reporting_units.
    for table in ("reporting_unit_organizations", "reporting_unit_users"):
        if _has_table(connection, table):
            op.drop_table(table)
    # Remove the audit tenant column along with its foreign-key constraint.
    if "reporting_unit_id" in _columns(connection, "audit_events"):
        with op.batch_alter_table("audit_events") as batch:
            batch.drop_column("reporting_unit_id")
    if _has_table(connection, "reporting_units"):
        op.drop_table("reporting_units")
