"""add partial coordinate index for map queries

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-22 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text


revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Indexa solo centros que pueden representarse en el mapa."""
    with op.get_context().autocommit_block():
        op.execute(
            text(
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persona_map_coordinates
                ON persona ((trim(lower(nombre_estado))), (trim(lower(nombre_municipio))), id)
                WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    """Elimina el índice parcial del mapa."""
    with op.get_context().autocommit_block():
        op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS ix_persona_map_coordinates"))