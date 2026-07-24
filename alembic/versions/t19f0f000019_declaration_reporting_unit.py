"""declarations.reporting_unit_id (tenant tag independent of organization)

A declaration was only tenant-scoped to a Cảng indirectly, through its
Organization's membership in reporting_unit_organizations. That breaks when a
declaration has NO organization (customer company left blank/unknown at
save time): the declaration becomes unreachable in every port-scoped list
query, since ``organization_id IN (...)`` never matches a NULL. This adds a
direct ``reporting_unit_id`` column so a declaration always stays visible to
the Cảng/unit that created it, whether or not a customer organization was
picked.

Existing rows are backfilled from their Organization's reporting-unit
membership when it is unambiguous (exactly one unit); rows left NULL keep
today's (broken) visibility until re-saved, since the correct unit cannot be
inferred with confidence.

Revision ID: t19f0f000019
Revises: s18f0f000018
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa


revision = "t19f0f000019"
down_revision = "s18f0f000018"
branch_labels = None
depends_on = None


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def upgrade() -> None:
    connection = op.get_bind()
    columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("declarations")}
        if _has_table(connection, "declarations") else set()
    )
    if columns and "reporting_unit_id" not in columns:
        op.execute(
            "ALTER TABLE declarations ADD COLUMN "
            "reporting_unit_id INTEGER REFERENCES reporting_units (id)"
        )
        op.create_index(
            "ix_declarations_reporting_unit_id",
            "declarations", ["reporting_unit_id"], unique=False,
        )
        # Backfill from the declaration's Organization membership, only where
        # the org belongs to exactly one reporting unit (unambiguous).
        op.execute(
            """
            UPDATE declarations
            SET reporting_unit_id = (
                SELECT ruo.reporting_unit_id
                FROM reporting_unit_organizations ruo
                WHERE ruo.organization_id = declarations.organization_id
                GROUP BY ruo.organization_id
                HAVING COUNT(*) = 1
            )
            WHERE declarations.organization_id IS NOT NULL
            """
        )


def downgrade() -> None:
    connection = op.get_bind()
    columns = (
        {column["name"] for column in sa.inspect(connection).get_columns("declarations")}
        if _has_table(connection, "declarations") else set()
    )
    if "reporting_unit_id" in columns:
        op.drop_index("ix_declarations_reporting_unit_id", table_name="declarations")
        with op.batch_alter_table("declarations") as batch_op:
            batch_op.drop_column("reporting_unit_id")
