"""add indexes for municipality center searches

Revision ID: c4d5e6f7a8b9
Revises: 3af91407ae16
Create Date: 2026-08-22 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text


revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "3af91407ae16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Indexa el filtro estatal, municipal y de centro de votación."""
    # El índice cubre las expresiones usadas por la consulta y evita un escaneo completo.
    with op.get_context().autocommit_block():
        op.execute(
            text(
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persona_municipality_center_search
                ON persona (
                    (trim(lower(nombre_estado))),
                    (trim(lower(nombre_municipio))),
                    (trim(nombre_cv)),
                    id
                )
                """
            )
        )


def downgrade() -> None:
    """Elimina el índice de búsqueda municipal."""
    with op.get_context().autocommit_block():
        op.execute(text("DROP INDEX CONCURRENTLY IF EXISTS ix_persona_municipality_center_search"))
