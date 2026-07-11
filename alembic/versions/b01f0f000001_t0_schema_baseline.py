"""t0_schema_baseline

Revision ID: b01f0f000001
Revises:
Create Date: 2026-07-11
"""
from alembic import op

revision = "b01f0f000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This baseline is intentionally part of Alembic, not runtime startup. It
    # creates any missing pilot tables without altering existing T0/T1 data.
    from backend.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # A baseline database is never dropped automatically. Rollback of later
    # revisions is supported; destructive full teardown requires an explicit
    # operator action outside the application migration command.
    pass
