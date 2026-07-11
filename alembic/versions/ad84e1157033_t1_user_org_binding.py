"""t1_user_org_binding

Revision ID: ad84e1157033
Revises:
Create Date: 2026-07-11 16:08:13.539315

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ad84e1157033'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add columns to users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', name='fk_users_organization_id'), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'))

    # 2. Disable existing unbound non-admin users
    # Enforces the security baseline: unbound customers must be disabled
    op.execute(
        "UPDATE users SET is_active = 0 WHERE role != 'ADMIN' AND organization_id IS NULL"
    )

def downgrade() -> None:
    # Remove columns from users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('organization_id')
        batch_op.drop_column('is_active')
