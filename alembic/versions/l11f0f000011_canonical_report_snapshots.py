"""add canonical report snapshots and audited PL.02 adjustments

Revision ID: l11f0f000011
Revises: k10f0f000010
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa


revision = "l11f0f000011"
down_revision = "k10f0f000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("declarations")}
    with op.batch_alter_table("declarations") as batch:
        if "departure_berth" not in columns:
            batch.add_column(sa.Column("departure_berth", sa.String(), nullable=False, server_default=""))
        if "agent_ptnd_name" not in columns:
            batch.add_column(sa.Column("agent_ptnd_name", sa.String(), nullable=False, server_default=""))
        if "is_passenger_call" not in columns:
            batch.add_column(sa.Column("is_passenger_call", sa.Integer(), nullable=False, server_default="0"))

    if not sa.inspect(connection).has_table("report_adjustments"):
        op.create_table(
            "report_adjustments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("report_kind", sa.String(), nullable=False, server_default="appendix2"),
            sa.Column("report_month", sa.String(), nullable=False),
            sa.Column("metric", sa.String(), nullable=False),
            sa.Column("delta", sa.Float(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
        )
        op.create_index("ix_report_adjustments_month", "report_adjustments", ["report_month"])


def downgrade() -> None:
    connection = op.get_bind()
    if sa.inspect(connection).has_table("report_adjustments"):
        indexes = {item["name"] for item in sa.inspect(connection).get_indexes("report_adjustments")}
        if "ix_report_adjustments_month" in indexes:
            op.drop_index("ix_report_adjustments_month", table_name="report_adjustments")
        op.drop_table("report_adjustments")
    columns = {column["name"] for column in sa.inspect(connection).get_columns("declarations")}
    with op.batch_alter_table("declarations") as batch:
        for name in ("is_passenger_call", "agent_ptnd_name", "departure_berth"):
            if name in columns:
                batch.drop_column(name)
