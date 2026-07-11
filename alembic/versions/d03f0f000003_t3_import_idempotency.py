"""t3_import_idempotency

Revision ID: d03f0f000003
Revises: c02f0f000002
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "d03f0f000003"
down_revision = "c02f0f000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "import_jobs" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("import_kind", sa.String(), nullable=False),
        sa.Column("source_checksum", sa.String(), nullable=False),
        sa.Column("mapping_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="COMPLETED"),
        sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("organization_id", "import_kind", "source_checksum", "mapping_version", name="uq_import_idempotency"),
    )


def downgrade() -> None:
    if "import_jobs" in inspect(op.get_bind()).get_table_names():
        op.drop_table("import_jobs")
