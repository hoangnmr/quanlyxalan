"""app_settings key-value store (for UI-editable settings like SMTP)

Adds a small key-value table so operations/admin can configure runtime settings
— currently the SMTP email server — from the web UI instead of the .env file.
Secret values inside a setting (SMTP password) are encrypted at the application
layer before being written here.

Revision ID: s18f0f000018
Revises: r17f0f000017
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "s18f0f000018"
down_revision = "r17f0f000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "app_settings" not in inspector.get_table_names():
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False, server_default=""),
            sa.Column("updated_at", sa.String(), nullable=False, server_default=""),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "app_settings" in inspector.get_table_names():
        op.drop_table("app_settings")
