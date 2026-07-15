"""normalize crew roles to the approved four-value catalog

Revision ID: i08f0f000008
Revises: h07f0f000007
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "i08f0f000008"
down_revision = "h07f0f000007"
branch_labels = None
depends_on = None


APPROVED_ROLES = ("Thuyền trưởng", "Máy trưởng", "Thuyền viên", "Thuyền phó")


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text(
        "UPDATE crew_members SET crew_role = 'Thuyền viên' "
        "WHERE crew_role NOT IN ('Thuyền trưởng', 'Máy trưởng', 'Thuyền viên', 'Thuyền phó')"
    ))


def downgrade() -> None:
    # The previous detailed role cannot be reconstructed after consolidation.
    pass
