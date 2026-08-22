---
name: diagnosticar-esquema-postgresql
description: "Diagnostica y corrige errores de PostgreSQL/SQLAlchemy como UndefinedColumn, relation does not exist y esquemas desfasados entre modelos y base de datos. Usa esta habilidad cuando una app Reflex o Python falla al consultar una columna, cuando Alembic y la base parecen estar fuera de sincronía, o antes de reiniciar un entorno con migraciones pendientes."
argument-hint: "Describe la excepción, la tabla/columna afectada y el comando con el que ejecutas la app"
user-invocable: true
---

# Diagnóstico De Esquema PostgreSQL

## Objetivo

Alinear de forma verificable el modelo de la aplicación, el historial de Alembic y la base PostgreSQL real, sin ocultar una migración fallida ni borrar datos para resolver un error de esquema.

## Cuándo Usar

- `psycopg2.errors.UndefinedColumn` o `sqlalchemy.exc.ProgrammingError` indica que falta una columna.
- La aplicación selecciona un campo que no existe en PostgreSQL.
- El modelo SQLModel/SQLAlchemy cambió, pero la base usada por la app no fue migrada.
- El arranque o el login de una app Reflex falla después de añadir permisos o campos.

## Procedimiento

1. **Fijar el síntoma y el contrato.** Extrae de la excepción el nombre exacto de la tabla y la columna, la consulta generada y el punto del código que la ejecuta. Localiza el modelo y la migración que deberían crear o modificar ese objeto.
2. **Comprobar la configuración efectiva.** Compara la URL de base de datos usada por Reflex, SQLAlchemy y Alembic. No asumas que `localhost`, el puerto, el nombre de base, el usuario o el entorno virtual son los mismos. Si hay variables de entorno, identifica cuál prevalece.
3. **Comprobar el historial sin modificar datos.** Ejecuta desde la raíz del proyecto:
   ```powershell
   alembic current
   alembic heads
   alembic history
   ```
   Confirma que existe una única cadena hasta `head` y que la revisión actual pertenece a esa cadena.
4. **Elegir la rama correcta.**
   - Si la revisión que añade el campo existe y la base está detrás, ejecuta `alembic upgrade head`.
   - Si Alembic apunta a otra base, corrige primero la configuración o la variable de entorno y repite la comprobación.
   - Si hay varias cabezas, una revisión faltante, o una migración incompatible con los datos existentes, detente y resuelve el historial; no marques manualmente la revisión como aplicada.
   - Si la migración ya figura aplicada pero el campo falta, inspecciona la base real y el contenido de la migración antes de crear otra migración.
5. **Validar el cambio en la base.** Consulta el catálogo de PostgreSQL o usa `\d usuario` en `psql` para verificar que la columna existe, tiene el tipo esperado, la nulabilidad correcta y el valor por defecto previsto. Para una columna nueva no nullable, confirma que la migración puede ejecutarse sobre las filas existentes.
6. **Reprobar el flujo original.** Reinicia `reflex run` si corresponde y repite exactamente la acción que falló, por ejemplo el login. Comprueba también una lectura y una escritura de la entidad afectada si el cambio modifica permisos o valores por defecto.
7. **Cerrar con evidencia.** Registra la revisión antes y después, la base objetivo, el comando ejecutado y el resultado del flujo original. Si la solución requiere editar una migración ya compartida o datos manuales, documenta esa decisión y su riesgo.

## Caso De Este Proyecto

En `bd_prueba`, `Usuario` declara `can_consultar` y `can_imprimir`, y la revisión `3af91407ae16` añade ambas columnas. El error `usuario.can_consultar` significa que el código ya está en una revisión más nueva que la base consultada. La comprobación mínima es:

```powershell
alembic current
alembic upgrade head
```

Después debe verificarse la tabla `usuario` y repetirse el login. La URL de Reflex está en `rxconfig.py`; la configuración de Alembic debe apuntar a la misma base mediante su `sqlalchemy.url` o la configuración equivalente del entorno.

## Criterios De Calidad

- Se identificó la tabla, columna y revisión responsable.
- Se confirmó que la app y Alembic apuntan a la misma base.
- La base se actualizó mediante migraciones, no mediante `create_all`, edición manual de `alembic_version` ni borrado de datos.
- La migración terminó sin errores y la columna se verificó en PostgreSQL.
- El flujo original se ejecutó de nuevo y no se ocultaron excepciones.
- Se informaron bloqueos, múltiples cabezas, migraciones parciales o diferencias entre entornos.

## Límites

No generes una migración nueva solo porque `upgrade head` no se ejecuta. Primero determina si el problema es una URL equivocada, una revisión ausente, una migración fallida o un esquema alterado manualmente. No recomiendes eliminar y recrear la base salvo que el usuario confirme que es un entorno desechable y acepte la pérdida de datos.
