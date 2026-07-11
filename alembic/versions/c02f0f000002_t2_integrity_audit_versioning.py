"""t2_integrity_audit_versioning

Revision ID: c02f0f000002
Revises: ad84e1157033
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "c02f0f000002"
down_revision = "ad84e1157033"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table in ("vessels", "crew_members", "declarations"):
        if table in inspect(op.get_bind()).get_table_names() and "version" not in _columns(table):
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    if "audit_events" in inspect(op.get_bind()).get_table_names():
        columns = _columns("audit_events")
        with op.batch_alter_table("audit_events") as batch_op:
            if "actor_user_id" not in columns:
                batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
            if "organization_id" not in columns:
                batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            if "correlation_id" not in columns:
                batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=False, server_default=""))

    if "declaration_events" in inspect(op.get_bind()).get_table_names():
        columns = _columns("declaration_events")
        with op.batch_alter_table("declaration_events") as batch_op:
            if "actor_user_id" not in columns:
                batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
            if "correlation_id" not in columns:
                batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=False, server_default=""))


def downgrade() -> None:
    for table, names in {
        "audit_events": ("correlation_id", "organization_id", "actor_user_id"),
        "declaration_events": ("correlation_id", "actor_user_id"),
        "declarations": ("version",),
        "crew_members": ("version",),
        "vessels": ("version",),
    }.items():
        if table not in inspect(op.get_bind()).get_table_names():
            continue
        columns = _columns(table)
        with op.batch_alter_table(table) as batch_op:
            for name in names:
                if name in columns:
                    batch_op.drop_column(name)
