"""separate the port vessel register from customer vessel records

Revision ID: k10f0f000010
Revises: j09f0f000009
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa


revision = "k10f0f000010"
down_revision = "j09f0f000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch:
        if "is_port_tracked" not in columns:
            batch.add_column(sa.Column("is_port_tracked", sa.Integer(), nullable=False, server_default="0"))
        if "port_tracking_updated_at" not in columns:
            batch.add_column(sa.Column("port_tracking_updated_at", sa.String(), nullable=True))

    # Records already populated from the internal tracking workbook in the
    # preceding tranche carry its captain/contact fields. Keep them visible in
    # the new internal register without classifying ordinary customer records.
    connection.execute(sa.text(
        "UPDATE vessels SET is_port_tracked = 1, port_tracking_updated_at = updated_at "
        "WHERE COALESCE(tracking_master_name, '') <> '' "
        "OR COALESCE(tracking_master_phone, '') <> ''"
    ))


def downgrade() -> None:
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch:
        if "port_tracking_updated_at" in columns:
            batch.drop_column("port_tracking_updated_at")
        if "is_port_tracked" in columns:
            batch.drop_column("is_port_tracked")
