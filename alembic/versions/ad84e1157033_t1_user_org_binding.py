"""t1_user_org_binding

Revision ID: ad84e1157033
Revises:
Create Date: 2026-07-11 16:08:13.539315

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'ad84e1157033'
down_revision: Union[str, Sequence[str], None] = "b01f0f000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    if "organization_id" not in columns or "is_active" not in columns:
        with op.batch_alter_table('users') as batch_op:
            if "organization_id" not in columns:
                batch_op.add_column(sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', name='fk_users_organization_id'), nullable=True))
            if "is_active" not in columns:
                batch_op.add_column(sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'))

    # 2. Disable existing unbound non-admin users
    # Enforces the security baseline: unbound customers must be disabled
    op.execute(
        "UPDATE users SET is_active = 0 WHERE role != 'ADMIN' AND organization_id IS NULL"
    )

def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("users")}
    with op.batch_alter_table('users') as batch_op:
        if "organization_id" in columns:
            batch_op.drop_column('organization_id')
        if "is_active" in columns:
            batch_op.drop_column('is_active')
