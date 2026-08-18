"""add_functional_name_indexes

Revision ID: a1b2c3d4e5f6
Revises: 9864fd7ebe5f
Create Date: 2026-08-18 12:00:00.000000

"""
from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '9864fd7ebe5f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Aplica los nuevos índices funcionales para búsquedas LIKE insensibles a mayúsculas."""
    # Se usa `varchar_pattern_ops` que está optimizado para búsquedas con LIKE 'prefijo%'.
    op.create_index('ix_persona_primer_nombre_lower_pattern', 'persona', [text('lower(primer_nombre) varchar_pattern_ops')], unique=False)
    op.create_index('ix_persona_primer_apellido_lower_pattern', 'persona', [text('lower(primer_apellido) varchar_pattern_ops')], unique=False)

def downgrade() -> None:
    """Revierte los índices funcionales."""
    op.drop_index('ix_persona_primer_apellido_lower_pattern', table_name='persona')
    op.drop_index('ix_persona_primer_nombre_lower_pattern', table_name='persona')