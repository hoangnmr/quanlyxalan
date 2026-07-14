"""port enterprise workflow

Revision ID: g06f0f000006
Revises: f05f0f000005
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "g06f0f000006"
down_revision = "f05f0f000005"
branch_labels = None
depends_on = None


LEGACY_COLUMNS = ("qlc_approval", "bp_approval", "permit_no", "issued_at", "revoked_at")


def upgrade() -> None:
    connection = op.get_bind()
    columns = {column["name"] for column in inspect(connection).get_columns("declarations")}
    connection.execute(sa.text(
        "UPDATE users SET role = 'PORT_STAFF' WHERE role IN ('CV', 'QLC', 'BP')"
    ))
    pending_reset = ", cv_approval = 'PENDING'" if "cv_approval" in columns else ""
    connection.execute(sa.text(
        "UPDATE declarations SET workflow_status = 'PENDING_REVIEW'" + pending_reset +
        " WHERE workflow_status IN ('PENDING_QLC', 'PENDING_BP')"
    ))
    connection.execute(sa.text(
        "UPDATE declarations SET workflow_status = 'APPROVED' WHERE workflow_status = 'ISSUED'"
    ))
    connection.execute(sa.text(
        "UPDATE declarations SET workflow_status = 'CHANGES_REQUESTED'" + pending_reset +
        " WHERE workflow_status = 'REVOKED'"
    ))

    with op.batch_alter_table("declarations") as batch_op:
        for column in LEGACY_COLUMNS:
            if column in columns:
                batch_op.drop_column(column)
        if "cv_approval" in columns:
            batch_op.alter_column(
                "cv_approval",
                new_column_name="port_approval",
                existing_type=sa.String(),
                existing_nullable=False,
            )
        elif "port_approval" not in columns:
            batch_op.add_column(sa.Column(
                "port_approval", sa.String(), nullable=False, server_default="PENDING"
            ))

    connection.execute(sa.text(
        "UPDATE declarations SET port_approval = CASE "
        "WHEN workflow_status = 'APPROVED' THEN 'APPROVED' ELSE 'PENDING' END"
    ))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("declarations")}
    with op.batch_alter_table("declarations") as batch_op:
        if "port_approval" in columns:
            batch_op.alter_column(
                "port_approval",
                new_column_name="cv_approval",
                existing_type=sa.String(),
                existing_nullable=False,
            )
        if "qlc_approval" not in columns:
            batch_op.add_column(sa.Column("qlc_approval", sa.String(), nullable=False, server_default="PENDING"))
        if "bp_approval" not in columns:
            batch_op.add_column(sa.Column("bp_approval", sa.String(), nullable=False, server_default="PENDING"))
        if "permit_no" not in columns:
            batch_op.add_column(sa.Column("permit_no", sa.String(), nullable=False, server_default=""))
        if "issued_at" not in columns:
            batch_op.add_column(sa.Column("issued_at", sa.String(), nullable=True))
        if "revoked_at" not in columns:
            batch_op.add_column(sa.Column("revoked_at", sa.String(), nullable=True))
