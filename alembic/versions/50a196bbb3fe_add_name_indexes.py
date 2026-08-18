"""add_name_indexes

Revision ID: 50a196bbb3fe
Revises: b7f5db3ef42e
Create Date: 2026-08-16 16:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '50a196bbb3fe'
down_revision: str | Sequence[str] | None = 'b7f5db3ef42e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Crear índices para primer nombre y primer apellido ###
    with op.batch_alter_table('persona', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_persona_primer_apellido'), ['primer_apellido'], unique=False)
        batch_op.create_index(batch_op.f('ix_persona_primer_nombre'), ['primer_nombre'], unique=False)
    # ### Fin de los comandos ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### Comandos para revertir los cambios ###
    with op.batch_alter_table('persona', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_persona_primer_nombre'))
        batch_op.drop_index(batch_op.f('ix_persona_primer_apellido'))
    # ### Fin de los comandos ###
