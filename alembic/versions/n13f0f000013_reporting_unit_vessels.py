"""per-port vessel register association (reporting_unit_vessels)

Adds an FK-backed, tenant-scoped port register association so the same physical
vessel can be tracked by one reporting unit and not another. The legacy global
``vessels.is_port_tracked`` boolean is retained for backward compatibility only
and is no longer the authorization or tenant boundary for the register.

This is a forward migration applied AFTER m12f0f000012; it does not modify the
already-applied m12 revision. It only ADDS a table and leaves existing rows
untouched.

Revision ID: n13f0f000013
Revises: m12f0f000012
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa


revision = "n13f0f000013"
down_revision = "m12f0f000012"
branch_labels = None
depends_on = None


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def upgrade() -> None:
    connection = op.get_bind()
    if not _has_table(connection, "reporting_unit_vessels"):
        op.create_table(
            "reporting_unit_vessels",
            sa.Column("reporting_unit_id", sa.Integer(),
                      sa.ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("vessel_id", sa.Integer(),
                      sa.ForeignKey("vessels.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("added_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False),
        )
    columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("report_adjustments")}
        if _has_table(connection, "report_adjustments") else set()
    )
    if columns and "reporting_unit_id" not in columns:
        op.execute(
            "ALTER TABLE report_adjustments ADD COLUMN "
            "reporting_unit_id INTEGER REFERENCES reporting_units (id)"
        )
        op.create_index(
            "ix_report_adjustments_reporting_unit_id",
            "report_adjustments", ["reporting_unit_id"], unique=False,
        )
    import_columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("import_jobs")}
        if _has_table(connection, "import_jobs") else set()
    )
    if import_columns and "reporting_unit_id" not in import_columns:
        op.execute(
            "ALTER TABLE import_jobs ADD COLUMN "
            "reporting_unit_id INTEGER REFERENCES reporting_units (id)"
        )
        op.create_index(
            "ix_import_jobs_reporting_unit_id",
            "import_jobs", ["reporting_unit_id"], unique=False,
        )
    sync_columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("sync_jobs")}
        if _has_table(connection, "sync_jobs") else set()
    )
    if sync_columns and "reporting_unit_id" not in sync_columns:
        op.execute(
            "ALTER TABLE sync_jobs ADD COLUMN "
            "reporting_unit_id INTEGER REFERENCES reporting_units (id)"
        )
        op.create_index(
            "ix_sync_jobs_reporting_unit_id",
            "sync_jobs", ["reporting_unit_id"], unique=False,
        )
    if not _has_table(connection, "reporting_unit_vessels"):
        raise RuntimeError("H2/R4 schema drift: reporting_unit_vessels was not created")


def downgrade() -> None:
    connection = op.get_bind()
    if _has_table(connection, "reporting_unit_vessels"):
        op.drop_table("reporting_unit_vessels")
    report_columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("report_adjustments")}
        if _has_table(connection, "report_adjustments") else set()
    )
    if "reporting_unit_id" in report_columns:
        op.drop_index("ix_report_adjustments_reporting_unit_id", table_name="report_adjustments")
        with op.batch_alter_table("report_adjustments") as batch_op:
            batch_op.drop_column("reporting_unit_id")
    import_columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("import_jobs")}
        if _has_table(connection, "import_jobs") else set()
    )
    if "reporting_unit_id" in import_columns:
        op.drop_index("ix_import_jobs_reporting_unit_id", table_name="import_jobs")
        with op.batch_alter_table("import_jobs") as batch_op:
            batch_op.drop_column("reporting_unit_id")
    sync_columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("sync_jobs")}
        if _has_table(connection, "sync_jobs") else set()
    )
    if "reporting_unit_id" in sync_columns:
        op.drop_index("ix_sync_jobs_reporting_unit_id", table_name="sync_jobs")
        with op.batch_alter_table("sync_jobs") as batch_op:
            batch_op.drop_column("reporting_unit_id")
