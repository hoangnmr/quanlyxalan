"""allow tenant-safe TOS links across source-file imports

Berth and container-detail data are supplied as separate workbooks, therefore
they necessarily have different historical_report_import rows.  The H2
foundation accidentally required cargo/link.import_id to equal call.import_id,
which made the audited 1:N Berth/detail join impossible to persist.  This
revision changes only the call-reference FK: it remains composite and
fail-closed on reporting_unit_id, while source provenance still points to each
row's own immutable import.

Revision ID: o14f0f000014
Revises: n13f0f000013
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa


revision = "o14f0f000014"
down_revision = "n13f0f000013"
branch_labels = None
depends_on = None


def _columns(connection, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(connection).get_columns(table)}


def _unique_names(connection, table: str) -> set[str]:
    return {
        item.get("name") for item in sa.inspect(connection).get_unique_constraints(table)
        if item.get("name")
    }


def _fk_columns(connection, table: str, name: str) -> list[str]:
    for item in sa.inspect(connection).get_foreign_keys(table):
        if item.get("name") == name:
            return list(item.get("constrained_columns") or [])
    return []


def upgrade() -> None:
    connection = op.get_bind()
    if "uq_hist_call_tenant_identity" not in _unique_names(connection, "historical_port_calls"):
        with op.batch_alter_table("historical_port_calls") as batch:
            batch.create_unique_constraint(
                "uq_hist_call_tenant_identity", ["id", "reporting_unit_id"]
            )

    cargo_columns = _columns(connection, "historical_cargo_rows")
    cargo_fk = _fk_columns(connection, "historical_cargo_rows", "fk_hist_cargo_call")
    if "call_key_normalized" not in cargo_columns or cargo_fk != ["port_call_id", "reporting_unit_id"]:
        with op.batch_alter_table("historical_cargo_rows") as batch:
            if "call_key_normalized" not in cargo_columns:
                batch.add_column(sa.Column(
                    "call_key_normalized", sa.String(), nullable=False, server_default=""
                ))
            if cargo_fk:
                batch.drop_constraint("fk_hist_cargo_call", type_="foreignkey")
            batch.create_foreign_key(
                "fk_hist_cargo_call", "historical_port_calls",
                ["port_call_id", "reporting_unit_id"], ["id", "reporting_unit_id"],
                ondelete="CASCADE",
            )

    link_fk = _fk_columns(connection, "historical_vessel_links", "fk_hist_link_call")
    if link_fk != ["port_call_id", "reporting_unit_id"]:
        with op.batch_alter_table("historical_vessel_links") as batch:
            if link_fk:
                batch.drop_constraint("fk_hist_link_call", type_="foreignkey")
            batch.create_foreign_key(
                "fk_hist_link_call", "historical_port_calls",
                ["port_call_id", "reporting_unit_id"], ["id", "reporting_unit_id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    connection = op.get_bind()
    cross_import_cargo = connection.execute(sa.text(
        "SELECT COUNT(*) FROM historical_cargo_rows c "
        "JOIN historical_port_calls p ON p.id = c.port_call_id "
        "AND p.reporting_unit_id = c.reporting_unit_id "
        "WHERE c.port_call_id IS NOT NULL AND c.import_id <> p.import_id"
    )).scalar() or 0
    cross_import_links = connection.execute(sa.text(
        "SELECT COUNT(*) FROM historical_vessel_links l "
        "JOIN historical_port_calls p ON p.id = l.port_call_id "
        "AND p.reporting_unit_id = l.reporting_unit_id "
        "WHERE l.port_call_id IS NOT NULL AND l.import_id <> p.import_id"
    )).scalar() or 0
    if cross_import_cargo or cross_import_links:
        raise RuntimeError(
            "Refusing o14 downgrade: n13 cannot represent existing cross-import "
            f"TOS links (cargo={cross_import_cargo}, vessel_links={cross_import_links})."
        )
    with op.batch_alter_table("historical_vessel_links") as batch:
        batch.drop_constraint("fk_hist_link_call", type_="foreignkey")
        batch.create_foreign_key(
            "fk_hist_link_call", "historical_port_calls",
            ["port_call_id", "import_id", "reporting_unit_id"],
            ["id", "import_id", "reporting_unit_id"], ondelete="CASCADE",
        )

    with op.batch_alter_table("historical_cargo_rows") as batch:
        batch.drop_constraint("fk_hist_cargo_call", type_="foreignkey")
        batch.create_foreign_key(
            "fk_hist_cargo_call", "historical_port_calls",
            ["port_call_id", "import_id", "reporting_unit_id"],
            ["id", "import_id", "reporting_unit_id"], ondelete="CASCADE",
        )
        batch.drop_column("call_key_normalized")

    with op.batch_alter_table("historical_port_calls") as batch:
        batch.drop_constraint("uq_hist_call_tenant_identity", type_="unique")
