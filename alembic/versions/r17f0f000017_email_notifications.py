"""email notifications: users.email + reporting_units.notify_email

Adds an email address to user accounts (previously users had no email column,
so port staff had no notification target) and a shared notification email to
each reporting unit (fallback recipient for a port). Both feed the opt-in email
notification feature; the per-user opt-in flags live inside the existing
``users.notification_preferences_json`` blob and need no schema change.

Revision ID: r17f0f000017
Revises: q16f0f000016
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "r17f0f000017"
down_revision = "q16f0f000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "email" not in user_columns:
            batch_op.add_column(sa.Column(
                "email", sa.String(), nullable=False, server_default=""
            ))
    unit_columns = {c["name"] for c in inspector.get_columns("reporting_units")}
    with op.batch_alter_table("reporting_units") as batch_op:
        if "notify_email" not in unit_columns:
            batch_op.add_column(sa.Column(
                "notify_email", sa.String(), nullable=False, server_default=""
            ))


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "email" in user_columns:
            batch_op.drop_column("email")
    unit_columns = {c["name"] for c in inspector.get_columns("reporting_units")}
    with op.batch_alter_table("reporting_units") as batch_op:
        if "notify_email" in unit_columns:
            batch_op.drop_column("notify_email")
