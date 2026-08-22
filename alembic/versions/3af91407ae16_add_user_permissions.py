"""add user permissions

Revision ID: 3af91407ae16
Revises: a1b2c3d4e5f6
Create Date: 2026-08-19 21:16:50.596948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '3af91407ae16'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('can_consultar', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        batch_op.add_column(sa.Column('can_imprimir', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.drop_column('can_imprimir')
        batch_op.drop_column('can_consultar')

