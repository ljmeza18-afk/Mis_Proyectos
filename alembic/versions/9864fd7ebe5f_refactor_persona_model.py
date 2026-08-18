"""refactor_persona_model

Revision ID: 9864fd7ebe5f
Revises: 50a196bbb3fe
Create Date: 2026-08-16 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa  # pyright: ignore[reportMissingImports]
from sqlalchemy import text  # pyright: ignore[reportMissingImports]

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9864fd7ebe5f'
down_revision: str | Sequence[str] | None = '50a196bbb3fe'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### Comandos manuales para refactorizar el modelo Persona y añadir FTS ###

    # 1. Crear la extensión unaccent y la configuración de búsqueda.
    #    Si esto falla por permisos, debe ser ejecutado manualmente en la BD por un superusuario:
    #    > CREATE EXTENSION IF NOT EXISTS unaccent;
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'public.spanish_unaccent') THEN
                CREATE TEXT SEARCH CONFIGURATION public.spanish_unaccent (COPY = pg_catalog.spanish);
                ALTER TEXT SEARCH CONFIGURATION public.spanish_unaccent
                ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;
            END IF;
        END $$;
    """)

    with op.batch_alter_table('persona', schema=None) as batch_op:
        # 1. Añadir todas las nuevas columnas, permitiendo nulos temporalmente
        batch_op.add_column(sa.Column('genero', sa.String(1), nullable=True))
        batch_op.add_column(sa.Column('nombre_estado', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('nombre_municipio', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('nombre_cv', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('direccion_cv', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('latitud', sa.Numeric(10, 8), nullable=True))
        batch_op.add_column(sa.Column('longitud', sa.Numeric(11, 8), nullable=True))

    # 2. Copiar datos de la columna 'sexo' a la nueva 'genero'
    op.execute('UPDATE persona SET genero = sexo')

    # 2.1. Rellenar con valores por defecto las nuevas columnas de texto para evitar errores de nulos.
    #      Esto es crucial para que la posterior restricción NOT NULL no falle en datos existentes.
    op.execute("UPDATE persona SET nombre_estado = '' WHERE nombre_estado IS NULL")
    op.execute("UPDATE persona SET nombre_municipio = '' WHERE nombre_municipio IS NULL")
    op.execute("UPDATE persona SET nombre_cv = '' WHERE nombre_cv IS NULL")
    op.execute("UPDATE persona SET direccion_cv = '' WHERE direccion_cv IS NULL")
    op.execute("UPDATE persona SET genero = '' WHERE genero IS NULL")

    with op.batch_alter_table('persona', schema=None) as batch_op:
        # 3. Eliminar la vieja columna 'sexo'
        batch_op.drop_column('sexo')
        
        # 4. Cambiar el tipo de la columna 'id' a BigInteger
        batch_op.alter_column('id', existing_type=sa.Integer(), type_=sa.BigInteger(), nullable=False)

        # 5. Cambiar el tipo y longitud de 'v_e'
        batch_op.alter_column('v_e', existing_type=sa.VARCHAR(), type_=sa.String(1), nullable=False, postgresql_using="COALESCE(NULLIF(v_e, ''), 'V')")

        # 6. Cambiar el tipo de 'cedula' a Integer
        batch_op.alter_column('cedula', existing_type=sa.VARCHAR(), type_=sa.Integer(), nullable=False, postgresql_using="NULLIF(cedula, '')::integer")

        # 7. Cambiar el tipo y longitud de 'primer_apellido'
        batch_op.alter_column('primer_apellido', existing_type=sa.VARCHAR(), type_=sa.String(100), nullable=False, postgresql_using="COALESCE(NULLIF(primer_apellido, ''), '')")

        # 8. Cambiar el tipo y longitud de 'segundo_apellido'
        batch_op.alter_column('segundo_apellido', existing_type=sa.VARCHAR(), type_=sa.String(100), nullable=False, postgresql_using="COALESCE(NULLIF(segundo_apellido, ''), '')")

        # 9. Cambiar el tipo y longitud de 'primer_nombre'
        batch_op.alter_column('primer_nombre', existing_type=sa.VARCHAR(), type_=sa.String(100), nullable=False, postgresql_using="COALESCE(NULLIF(primer_nombre, ''), '')")

        # 10. Cambiar el tipo y longitud de 'segundo_nombre'
        batch_op.alter_column('segundo_nombre', existing_type=sa.VARCHAR(), type_=sa.String(100), nullable=False, postgresql_using="COALESCE(NULLIF(segundo_nombre, ''), '')")

        # 11. Cambiar el tipo y longitud de 'nombre_completo'
        batch_op.alter_column('nombre_completo', existing_type=sa.VARCHAR(), type_=sa.String(400), nullable=False, postgresql_using="COALESCE(NULLIF(nombre_completo, ''), '')")

        # 12. Renombrar 'cod_cv' a 'codigo_cv' y cambiar su tipo a Integer
        # Nota: El existing_type para 'cod_cv' antes de este cambio era VARCHAR (de la migración b7f5db3ef42e)
        batch_op.alter_column('cod_cv', new_column_name='codigo_cv', existing_type=sa.VARCHAR(), type_=sa.Integer(), nullable=True, postgresql_using="NULLIF(cod_cv, '')::integer")

        # 13. Cambiar el tipo de 'fecha_nacimiento' a Date y permitir nulos (originalmente era NOT NULL)
        batch_op.alter_column('fecha_nacimiento',
            existing_type=sa.VARCHAR(),
            type_=sa.Date(),
            nullable=True,
            postgresql_using="NULLIF(fecha_nacimiento, '')::date")

        # 14. Cambiar el tipo de 'estado' a Integer y permitir nulos (originalmente era NOT NULL)
        batch_op.alter_column('estado',
            existing_type=sa.VARCHAR(),
            type_=sa.Integer(),
            nullable=True,
            postgresql_using="NULLIF(estado, '')::integer")

        # 15. Cambiar el tipo de 'municipio' a Integer y permitir nulos (originalmente era NOT NULL)
        batch_op.alter_column('municipio',
            existing_type=sa.VARCHAR(),
            type_=sa.Integer(),
            nullable=True,
            postgresql_using="NULLIF(municipio, '')::integer")

        # 16. Cambiar el tipo de 'parroquia' a Integer y permitir nulos (originalmente era NOT NULL)
        batch_op.alter_column('parroquia',
            existing_type=sa.VARCHAR(),
            type_=sa.Integer(),
            nullable=True,
            postgresql_using="NULLIF(parroquia, '')::integer")

        # 17. Hacer que las nuevas columnas de texto no acepten nulos y tengan un valor por defecto
        batch_op.alter_column('genero', existing_type=sa.String(1), type_=sa.String(1), nullable=False, server_default='')
        batch_op.alter_column('nombre_estado', existing_type=sa.String(50), type_=sa.String(50), nullable=False, server_default='')
        batch_op.alter_column('nombre_municipio', existing_type=sa.String(100), type_=sa.String(100), nullable=False, server_default='')
        batch_op.alter_column('nombre_cv', existing_type=sa.String(255), type_=sa.String(255), nullable=False, server_default='')
        batch_op.alter_column('direccion_cv', existing_type=sa.Text(), type_=sa.Text(), nullable=False, server_default='')

        # 18. Latitud y Longitud ya fueron añadidas con el tipo correcto (Numeric) y nullable=True.
        # No se necesita alter_column adicional para ellas si ya se añadieron correctamente.
        # Si se hubieran añadido como Float y ahora se quisieran cambiar a Numeric, se haría aquí.
        # Como se añadieron directamente como Numeric, no se requiere alteración posterior.

    # 19. Crear el índice de Búsqueda de Texto Completo (GIN) en la columna ya refactorizada.
    op.create_index(
        'ix_persona_nombre_completo_fts',
        'persona',
        [text("to_tsvector('public.spanish_unaccent', nombre_completo)")],
        postgresql_using='gin'
    )

    # ### Fin de los comandos ###


def downgrade() -> None:
    # ### Comandos manuales para revertir el refactor ###

    # 0. Eliminar el índice FTS que se creó en el upgrade.
    op.drop_index('ix_persona_nombre_completo_fts', table_name='persona', postgresql_using='gin')

    with op.batch_alter_table('persona', schema=None) as batch_op:
        # 1. Añadir la columna 'sexo' de vuelta
        batch_op.add_column(sa.Column('sexo', sa.VARCHAR(), nullable=False, server_default='')) # Original era NOT NULL

    # 2. Copiar datos de 'genero' a 'sexo'
    op.execute('UPDATE persona SET sexo = genero')

    with op.batch_alter_table('persona', schema=None) as batch_op:
        # 3. Revertir nullable y server_default para las nuevas columnas de texto
        batch_op.alter_column('direccion_cv', existing_type=sa.Text(), nullable=True, server_default=None)
        batch_op.alter_column('nombre_cv', existing_type=sa.String(255), nullable=True, server_default=None)
        batch_op.alter_column('nombre_municipio', existing_type=sa.String(100), nullable=True, server_default=None)
        batch_op.alter_column('nombre_estado', existing_type=sa.String(50), nullable=True, server_default=None)
        batch_op.alter_column('genero', existing_type=sa.String(1), nullable=True, server_default=None)

        # 4. Revertir cambio de tipos para codigo_cv, parroquia, municipio, estado, fecha_nacimiento
        #    Volvemos a VARCHAR y nullable=False como estaban en la migración b7f5db3ef42e
        batch_op.alter_column('codigo_cv',
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            nullable=False, # Original era nullable=False
            postgresql_using='codigo_cv::text')
        batch_op.alter_column('parroquia',
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            nullable=False, # Original era nullable=False
            postgresql_using='parroquia::text')
        batch_op.alter_column('municipio',
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            nullable=False, # Original era nullable=False
            postgresql_using='municipio::text')
        batch_op.alter_column('estado',
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            nullable=False, # Original era nullable=False
            postgresql_using='estado::text')
        batch_op.alter_column('fecha_nacimiento',
            existing_type=sa.Date(),
            type_=sa.VARCHAR(),
            nullable=False, # Original era nullable=False
            postgresql_using='fecha_nacimiento::text')

        # 5. Revertir tipos y longitudes para las columnas de texto existentes
        batch_op.alter_column('nombre_completo', existing_type=sa.String(400), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('segundo_nombre', existing_type=sa.String(100), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('primer_nombre', existing_type=sa.String(100), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('segundo_apellido', existing_type=sa.String(100), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('primer_apellido', existing_type=sa.String(100), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('cedula', existing_type=sa.Integer(), type_=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('v_e', existing_type=sa.String(1), type_=sa.VARCHAR(), nullable=False)

        # 6. Revertir 'id' a Integer
        batch_op.alter_column('id', existing_type=sa.BigInteger(), type_=sa.Integer(), nullable=False)

        # 7. Revertir renombre de 'codigo_cv' a 'cod_cv'
        # Nota: El existing_type para 'codigo_cv' ahora es Integer (después del upgrade)
        batch_op.alter_column('codigo_cv', new_column_name='cod_cv', existing_type=sa.Integer(), nullable=False) # Original era nullable=False

        # 8. Eliminar las nuevas columnas añadidas en el upgrade
        batch_op.drop_column('genero')
        batch_op.drop_column('nombre_estado')
        batch_op.drop_column('nombre_municipio')
        batch_op.drop_column('nombre_cv')
        batch_op.drop_column('direccion_cv')
        batch_op.drop_column('latitud')
        batch_op.drop_column('longitud')

    # 9. Eliminar la configuración de búsqueda y la extensión.
    #    Esto se hace al final para no romper dependencias.
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS public.spanish_unaccent;")
    op.execute("DROP EXTENSION IF EXISTS unaccent;")
    # ### Fin de los comandos ###
