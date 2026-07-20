"""vessel_category: optional internal classification, separate from vessel_type

vessel_type holds the "Công dụng" value transcribed verbatim from the vessel's
GCN (e.g. "Chở hàng khô hoặc container") and is required, since it is what
Phụ lục 1/3 print in their Công dụng/Loại phương tiện columns. It was
previously conflated with an unrelated internal craft-type catalog (Tàu hàng
khô, Tàu container, Sà lan…) that has no basis in any official document. This
revision gives that catalog its own optional column so it stops overwriting
transcribed certificate text.

Revision ID: p15f0f000015
Revises: o14f0f000014
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "p15f0f000015"
down_revision = "o14f0f000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch_op:
        if "vessel_category" not in columns:
            batch_op.add_column(sa.Column("vessel_category", sa.String(), nullable=True))


def downgrade() -> None:
    columns = {c["name"] for c in inspect(op.get_bind()).get_columns("vessels")}
    with op.batch_alter_table("vessels") as batch_op:
        if "vessel_category" in columns:
            batch_op.drop_column("vessel_category")
