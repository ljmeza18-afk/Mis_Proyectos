"""Por Leobaldo Meza."""
import csv
import datetime
import functools
import io
import re

import reflex as rx  # type: ignore[reportMissingImports]

try:
    import sqlmodel  # type: ignore[reportMissingImports]
except ImportError:  # type: ignore[reportMissingImports]

    class _MissingSQLModel:
        def __getattr__(self, name):
            raise ImportError("sqlmodel es requerido para usar la base de datos")

    sqlmodel = _MissingSQLModel()


class InvalidRowError(Exception):
    """Error para filas CSV inválidas."""

try:
    from reportlab.lib import colors  # type: ignore[reportMissingImports]
    from reportlab.lib.pagesizes import letter  # type: ignore[reportMissingImports]
    from reportlab.lib.styles import (  # type: ignore[reportMissingImports]
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.platypus import (  # type: ignore[reportMissingImports]
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:

    class _Missing:
        def __init__(self, *args, **kwargs):
            raise ImportError("reporte lab es requerido para características de PDF")

    class colors:
        black = "black"
        white = "white"

    letter = (612, 792)

    def ParagraphStyle(*args, **kwargs):
        raise ImportError("reportlab is required for ParagraphStyle")

    def getSampleStyleSheet():
        raise ImportError("reportlab is required for getSampleStyleSheet")

    Image = _Missing
    HRFlowable = _Missing
    Paragraph = _Missing
    SimpleDocTemplate = _Missing
    Spacer = _Missing
    Table = _Missing
    TableStyle = _Missing
from sqlalchemy import insert  # type: ignore[import]

# ==========================================
# 1. MODELOS DE BASE DE DATOS (SQLMODEL)
# ==========================================

class Usuario(rx.Model, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    username: str = sqlmodel.Field(unique=True, index=True)
    password: str
    rol: str = "admin"  # 'admin' o 'usuario'
    activo: bool = True


class Persona(rx.Model, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    v_e: str = ""
    cedula: int = sqlmodel.Field(index=True)
    primer_apellido: str = sqlmodel.Field(index=True)
    segundo_apellido: str = ""
    primer_nombre: str = sqlmodel.Field(index=True)
    segundo_nombre: str = ""
    nombre_completo: str = sqlmodel.Field(index=True)
    genero: str = ""  # Cambiado de 'sexo' a 'genero'
    fecha_nacimiento: datetime.date | None = None
    estado: int | None = None
    municipio: int | None = None
    parroquia: int | None = None
    codigo_cv: int | None = None

    # Nuevas columnas
    nombre_estado: str = ""
    nombre_municipio: str = ""
    nombre_cv: str = ""
    direccion_cv: str = ""
    latitud: float | None = None
    longitud: float | None = None


# ==========================================
# 2. ESTADO DE LA APLICACIÓN (BACKEND)
# ==========================================

class State(rx.State):
    # Autenticación
    logged_user: Usuario | None = None
    input_user: str = ""
    input_pass: str = ""
    error_msg: str = ""

    # UI State
    show_sidebar: bool = False
    current_dashboard_view: str = "search"

    # Búsqueda
    search_query: str = ""
    search_cedula: str = ""
    search_primer_nombre: str = ""
    search_primer_apellido: str = ""
    resultados: list[Persona] = sqlmodel.Field(default_factory=list)
    is_loading: bool = False
    sort_column: str = "nombre_completo"
    sort_order: str = "asc"

    # Paginación
    current_page: int = 1
    page_size: int = 10
    total_results: int = 0

    # Admin Users
    users: list[Usuario] = sqlmodel.Field(default_factory=list)
    show_edit_user_dialog: bool = False
    editing_user: Usuario | None = None
    show_delete_user_dialog: bool = False
    deleting_user: Usuario | None = None
    new_password_input: str = ""
    new_user_username: str = ""
    new_user_password: str = ""
    new_user_rol: str = "usuario"
    form_message: str = ""
    form_message_color: str = "red"

    # Constantes de la clase
    BATCH_SIZE = 10000  # Lote para la carga masiva


    # Estado de Carga Masiva
    upload_status: str = ""
    uploading: bool = False
    upload_progress: int | None = 0
    cancel_upload: bool = False
    upload_error_log: list[dict] = sqlmodel.Field(default_factory=list)
    upload_error_file_content: str | None = None

    upload_status_opacity: float = 0.0
    show_upload_dialog: bool = False

    @rx.var
    def upload_status_icon(self) -> str:
        """Devuelve el icono adecuado según el estado de la carga."""
        if self.upload_status.startswith("¡Éxito!"):
            return "check-circle-2"
        if self.upload_status.startswith("Error"):
            return "triangle-alert"
        return "info"

    @rx.var
    def upload_status_color(self) -> str:
        """Devuelve el color adecuado según el estado de la carga."""
        if self.upload_status.startswith("¡Éxito!"):
            return "green"
        if self.upload_status.startswith("Error"):
            return "red"
        return "blue"

    @rx.var
    def has_search_terms(self) -> bool:
        """Comprueba si alguno de los campos de búsqueda tiene texto."""
        return bool(
            self.search_cedula.strip()
            or self.search_primer_nombre.strip()
            or self.search_primer_apellido.strip()
        )

    # Setters explícitos
    def set_search_query(self, value: str):
        self.search_query = value

    def set_show_upload_dialog(self, value: bool):
        self.show_upload_dialog = value
        if value: # Si se está abriendo el diálogo, resetear el estado de la carga
            self.upload_status = ""
            self.upload_progress = 0
            self.uploading = False
            self.upload_error_log.clear()
            self.upload_error_file_content = None

    def set_search_cedula(self, value: str):
        self.search_cedula = value

    def set_search_primer_nombre(self, value: str):
        self.search_primer_nombre = value

    def set_search_primer_apellido(self, value: str):
        self.search_primer_apellido = value

    def set_input_user(self, value: str):
        self.input_user = value

    def set_input_pass(self, value: str):
        self.input_pass = value

    def set_new_user_username(self, value: str):
        self.new_user_username = value

    def set_new_user_password(self, value: str):
        self.new_user_password = value

    def set_new_user_rol(self, value: str):
        self.new_user_rol = value

    def set_editing_user_rol(self, rol: str):
        if self.editing_user:
            self.editing_user.rol = rol

    def set_editing_user_activo(self, activo: bool):
        if self.editing_user:
            self.editing_user.activo = activo

    def set_new_password_input(self, password: str):
        self.new_password_input = password

    def crear_usuario_inicial(self):
        """Crea el usuario administrador inicial si no existe."""
        with rx.session() as session:
            admin_existente = session.exec(
                sqlmodel.select(Usuario).where(Usuario.username == "admin")
            ).first()
            if not admin_existente:
                admin = Usuario(
                    username="admin",
                    password="admin123",
                    rol="admin",
                    activo=True,
                )
                session.add(admin)
                session.commit()

    def toggle_sidebar(self):
        self.show_sidebar = not self.show_sidebar

    def set_dashboard_view(self, view_name: str):
        self.current_dashboard_view = view_name
        if view_name == "admin_users": self.load_users()

    def login(self):
        self.error_msg = ""
        with rx.session() as session:
            user = session.exec(
                sqlmodel.select(Usuario).where(Usuario.username == self.input_user)
            ).first()
            if user and user.password == self.input_pass:
                self.logged_user = user
                self.input_pass = ""
            else:
                self.error_msg = "Usuario o contraseña incorrectos."

    def logout(self):
        self.logged_user = None
        self.current_dashboard_view = "search" # Reset view

    def load_users(self):
        with rx.session() as session:
            self.users = session.exec(sqlmodel.select(Usuario)).all()

    def set_show_edit_user_dialog(self, show: bool):
        """Controla la visibilidad del diálogo y recarga los datos al cerrar."""
        self.show_edit_user_dialog = show
        if not show:
            self.editing_user = None
            self.load_users()

    def start_edit_user(self, user: Usuario):
        """Prepara el diálogo para editar un usuario."""
        self.editing_user = user
        self.new_password_input = ""
        self.set_show_edit_user_dialog(True)

    def save_user_changes(self):
        """Guarda los cambios del usuario editado en la base de datos."""
        if not self.editing_user:
            return
        with rx.session() as session:
            db_user = session.get(Usuario, self.editing_user.id)
            if db_user:
                db_user.rol = self.editing_user.rol
                db_user.activo = self.editing_user.activo
                if self.new_password_input.strip():
                    db_user.password = self.new_password_input.strip()
                session.add(db_user)
                session.commit()
        
        # Cierra el diálogo y recarga la lista
        self.set_show_edit_user_dialog(False)

    def crear_nuevo_usuario(self):
        """Crea un nuevo usuario desde el panel de administración."""
        self.form_message = ""
        if not self.new_user_username.strip() or not self.new_user_password.strip():
            self.form_message = "El nombre de usuario y la contraseña no pueden estar vacíos."
            self.form_message_color = "red"
            return

        with rx.session() as session:
            existing_user = session.exec(
                sqlmodel.select(Usuario).where(Usuario.username == self.new_user_username.strip())
            ).first()
            if existing_user:
                self.form_message = "El nombre de usuario ya existe."
                self.form_message_color = "red"
                return

            new_user = Usuario(
                username=self.new_user_username.strip(),
                password=self.new_user_password.strip(),
                rol=self.new_user_rol,
                activo=True
            )
            session.add(new_user)
            session.commit()
            self.form_message = f"Usuario '{self.new_user_username.strip()}' creado con éxito."
            self.form_message_color = "green"
            self.new_user_username = ""
            self.new_user_password = ""
            self.limpiar_busqueda()
            return self.load_users

    def start_delete_user(self, user: Usuario):
        """Prepara el diálogo para eliminar un usuario."""
        self.deleting_user = user
        self.show_delete_user_dialog = True

    def set_show_delete_user_dialog(self, show: bool):
        """Controla la visibilidad del diálogo de eliminación."""
        self.show_delete_user_dialog = show
        if not show:
            self.deleting_user = None

    def delete_user(self):
        """Elimina el usuario seleccionado."""
        if not self.deleting_user or self.deleting_user.username == "admin":
            # Cierra el diálogo y no hace nada si es admin o no hay usuario
            self.set_show_delete_user_dialog(False)
            return

        with rx.session() as session:
            db_user = session.get(Usuario, self.deleting_user.id)
            if db_user:
                session.delete(db_user)
                session.commit()
        
        # Cierra el diálogo y recarga la lista
        self.set_show_delete_user_dialog(False)
        return self.load_users()

    def clear_upload_status(self):
        """Inicia la animación de desvanecimiento para el mensaje de estado."""
        self.upload_status_opacity = 0.0
        # Programa la limpieza real del texto después de que termine la animación
        yield rx.call_script(
            f"setTimeout(() => {{ if (window.reflex) window.reflex.call_event('{self.get_full_name()}._really_clear_status'); }}, 500)"
        )

    def _really_clear_status(self):
        """Limpia el texto del estado después de la animación. No llamar directamente."""
        self.upload_status = ""

    def _set_final_status(self, message: str, toast_kind: str, close_dialog: bool = False):
        """Establece el mensaje final, muestra un toast y programa su limpieza."""
        self.upload_status = message
        self.upload_status_opacity = 1.0
        toast_map = {
            "success": rx.toast.success,
            "warning": rx.toast.warning,
            "error": rx.toast.error,
            "info": rx.toast.info,
        }
        if toast_kind in toast_map:
            yield toast_map[toast_kind](message)
        
        yield rx.call_script(
            f"setTimeout(() => {{ if (window.reflex) window.reflex.call_event('{self.get_full_name()}.clear_upload_status'); }}, 8000)"
        )
        if close_dialog:
            # Programa el cierre del diálogo después de un breve retraso para permitir ver el mensaje final
            yield rx.call_script(
                f"setTimeout(() => {{ if (window.reflex) window.reflex.call_event('{self.get_full_name()}.set_show_upload_dialog', false); }}, 1000)"
            )

    def cancel_current_upload(self):
        """Cancela la carga de archivos en progreso."""
        self.cancel_upload = True
        self.upload_progress = 0
        self.uploading = False
        yield from self._set_final_status("Carga cancelada por el usuario.", "info")

    def download_error_log(self):
        """Descarga el log de errores de la última carga masiva."""
        if not self.upload_error_file_content:
            return rx.toast.error("No hay un log de errores para descargar.")
        
        return rx.download(
            data=self.upload_error_file_content.encode("utf-8-sig"), # Use utf-8-sig for better Excel compatibility
            filename=f"upload_errors_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        )
    
    @rx.var
    def total_pages(self) -> int:
        """Calcula el número total de páginas."""
        if self.total_results == 0:
            return 1
        return (self.total_results + self.page_size - 1) // self.page_size

    def next_page(self):
        """Va a la página siguiente."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            return State.buscar_persona

    def prev_page(self):
        """Va a la página anterior."""
        if self.current_page > 1:
            self.current_page -= 1
            return State.buscar_persona

    def go_to_page(self, page_num: int):
        self.current_page = page_num
        return State.buscar_persona

    def set_sort_order(self, column: str):
        """Establece la columna y el orden para ordenar los resultados."""
        if self.sort_column == column:
            self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        else:
            self.sort_column = column
            self.sort_order = "asc"
        self.current_page = 1
        return State.buscar_persona

    def buscar_persona(self, new_search: bool = False):
        """Realiza la búsqueda con paginación y muestra un indicador de carga."""
        self.is_loading = True
        if new_search:
            self.current_page = 1
        yield
        try:
            search_cedula_term = self.search_cedula.strip()
            search_nombre_term = self.search_primer_nombre.strip().lower()
            search_apellido_term = self.search_primer_apellido.strip().lower()

            with rx.session() as session:
                conditions = []

                if search_cedula_term:
                    cedula_match = re.match(r"^(V|E|v|e)?[\s-]*(\d{1,9})$", search_cedula_term)
                    if cedula_match:
                        v_e = cedula_match.group(1)
                        cedula_num = int(cedula_match.group(2))
                        cedula_condition = Persona.cedula == cedula_num
                        if v_e:
                            cedula_condition = sqlmodel.and_(
                                Persona.v_e == v_e.upper(), cedula_condition
                            )
                        conditions.append(cedula_condition)
                    else:
                        # Si la cédula tiene un formato inválido, no devolver resultados.
                        conditions.append(sqlmodel.false())

                if search_nombre_term:
                    conditions.append(sqlmodel.func.lower(Persona.primer_nombre).like(f"{search_nombre_term}%"))

                if search_apellido_term:
                    conditions.append(sqlmodel.func.lower(Persona.primer_apellido).like(f"{search_apellido_term}%"))

                if not conditions:
                    self.resultados, self.total_results = [], 0
                    return

                final_condition = sqlmodel.and_(*conditions)
                base_query = sqlmodel.select(Persona).where(final_condition)

                # Get total count of results only on a new search
                if new_search:
                    count_query = sqlmodel.select(sqlmodel.func.count(Persona.id)).where(final_condition)
                    self.total_results = session.exec(count_query).one()

                # Apply sorting
                sort_attribute = getattr(Persona, self.sort_column)
                order = sqlmodel.asc if self.sort_order == "asc" else sqlmodel.desc
                sorted_query = base_query.order_by(order(sort_attribute))

                # Apply pagination
                offset = (self.current_page - 1) * self.page_size
                paginated_query = sorted_query.offset(offset).limit(self.page_size)
                self.resultados = session.exec(paginated_query).all()
        finally:
            self.is_loading = False

    def limpiar_busqueda(self):
        """Limpia el campo de búsqueda y los resultados."""
        self.search_cedula = ""
        self.search_primer_nombre = ""
        self.search_primer_apellido = ""
        self.resultados = []
        self.total_results = 0
        self.current_page = 1

    @staticmethod
    def _process_row_to_dict(row: list[str], line_number: int) -> dict:
        """
        Transforma una fila de CSV en un diccionario para la inserción en la BD.
        Lanza InvalidRowError si la fila es inválida.
        """

        def to_int_or_none(val: str) -> int | None:
            """Convierte una cadena a entero, o devuelve None si está vacía o no es válida."""
            if not val:
                return None
            try:
                return int(val)
            except (ValueError, TypeError):
                return None

        def to_date_or_none(val: str) -> datetime.date | None:
            """Convierte una cadena a fecha, probando formatos comunes."""
            if not val:
                return None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):  # Common date formats
                try:
                    # datetime.strptime() crea un objeto naive; se marca como UTC para
                    # evitar el aviso DTZ007 sin cambiar el tipo de dato devuelto.
                    return datetime.datetime.strptime(val, fmt).replace(
                        tzinfo=datetime.timezone.utc
                    ).date()
                except ValueError:
                    continue
            return None

        def to_float_or_none(val: str) -> float | None:
            """Convierte una cadena a flotante, o devuelve None si está vacía o no es válida."""
            if not val:
                return None
            try:
                # Reemplazar coma por punto para decimales, común en algunos formatos de CSV
                return float(val.replace(',', '.'))
            except (ValueError, TypeError):
                return None

        # Extraer y limpiar todas las celdas de una vez para evitar llamadas repetidas a get_cell
        # Asegurarse de que la fila tenga al menos el número de columnas esperado
        num_expected_cols = 18
        cleaned_row = [
            (row[i].strip().strip('"').strip("'") if i < len(row) and row[i] else "")
            for i in range(num_expected_cols)
        ]

        # Mapeo de índices a nombres de columnas para mayor legibilidad
        V_E_COL = 0
        CEDULA_COL = 1
        PRIMER_APELLIDO_COL = 2
        SEGUNDO_APELLIDO_COL = 3
        PRIMER_NOMBRE_COL = 4
        SEGUNDO_NOMBRE_COL = 5
        GENERO_COL = 6
        FECHA_NACIMIENTO_COL = 7
        ESTADO_COL = 8
        MUNICIPIO_COL = 9
        PARROQUIA_COL = 10
        CODIGO_CV_COL = 11
        NOMBRE_ESTADO_COL = 12
        NOMBRE_MUNICIPIO_COL = 13
        NOMBRE_CV_COL = 14
        DIRECCION_CV_COL = 15
        LATITUD_COL = 16
        LONGITUD_COL = 17

        cedula_str = cleaned_row[CEDULA_COL]
        try:
            cedula_int = int(cedula_str)
        except ValueError:
            raise InvalidRowError(f"Línea {line_number}: La Cédula '{cedula_str}' (columna {CEDULA_COL + 1}) no es un número válido.")

        p_nombre = cleaned_row[PRIMER_NOMBRE_COL]
        p_apellido = cleaned_row[PRIMER_APELLIDO_COL]
        if not p_nombre or not p_apellido:
            raise InvalidRowError(f"Línea {line_number}: El primer nombre (columna {PRIMER_NOMBRE_COL + 1}) y el primer apellido (columna {PRIMER_APELLIDO_COL + 1}) son obligatorios.")

        s_nombre = cleaned_row[SEGUNDO_NOMBRE_COL]
        s_apellido = cleaned_row[SEGUNDO_APELLIDO_COL]
        
        partes_nombre = [p_nombre, s_nombre, p_apellido, s_apellido]
        nombre_concatenado = " ".join(p for p in partes_nombre if p)

        return {  # type: ignore
            "v_e": cleaned_row[V_E_COL] or "V", "cedula": cedula_int,
            "primer_apellido": p_apellido, "segundo_apellido": s_apellido,
            "primer_nombre": p_nombre, "segundo_nombre": s_nombre,
            "nombre_completo": nombre_concatenado,
            "genero": cleaned_row[GENERO_COL],
            "fecha_nacimiento": to_date_or_none(cleaned_row[FECHA_NACIMIENTO_COL]),
            "estado": to_int_or_none(cleaned_row[ESTADO_COL]),
            "municipio": to_int_or_none(cleaned_row[MUNICIPIO_COL]),
            "parroquia": to_int_or_none(cleaned_row[PARROQUIA_COL]),
            "codigo_cv": to_int_or_none(cleaned_row[CODIGO_CV_COL]),
            "nombre_estado": cleaned_row[NOMBRE_ESTADO_COL],
            "nombre_municipio": cleaned_row[NOMBRE_MUNICIPIO_COL],
            "nombre_cv": cleaned_row[NOMBRE_CV_COL],
            "direccion_cv": cleaned_row[DIRECCION_CV_COL],
            "latitud": to_float_or_none(cleaned_row[LATITUD_COL]),
            "longitud": to_float_or_none(cleaned_row[LONGITUD_COL]),
        }

    def handle_upload_progress(self, progress: dict):
        """Actualiza el estado de la carga."""
        self.upload_progress = int(progress["progress"] * 100)

    @staticmethod
    def _batch_insert(data: list[dict]):
        """Inserta un lote de datos en la base de datos en un hilo separado para no bloquear."""
        with rx.session() as session:
            session.execute(insert(Persona), data)
            session.commit()

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Procesa la subida masiva de forma ultra eficiente usando streaming y SQL Core."""
        self.cancel_upload = False # Reset cancellation flag at the start of a new upload
        self.upload_error_log.clear()
        self.upload_error_file_content = None
        if not files:
            for event in self._set_final_status("Por favor, seleccione un archivo primero.", "warning"):
                yield event
            return

        for file in files:
            self.uploading = True
            self.upload_status = "Archivo en servidor. Iniciando procesamiento..."
            self.upload_progress = 0
            yield

            line_number = 0
            delimiter = ","
            try:
                file_size = file.size or 1
                bytes_processed = 0

                # --- 1. Detección de codificación y delimitador por streaming ---
                # En versiones recientes de Reflex, rx.UploadFile no es un iterador asíncrono.
                # Leemos un primer trozo para detectar la codificación y luego reiniciamos.
                first_chunk_sample = await file.read(4096)
                if not first_chunk_sample:
                    for event in self._set_final_status("El archivo está vacío.", "warning"):
                        yield event
                    continue
                
                # Es crucial volver al inicio del archivo para procesarlo completo.
                await file.seek(0)

                self.upload_status = "Detectando formato del archivo..."
                yield
                try:
                    first_lines_sample = first_chunk_sample.decode("utf-8-sig")
                    encoding = "utf-8-sig"
                except UnicodeDecodeError:
                    first_lines_sample = first_chunk_sample.decode("latin-1")
                    encoding = "latin-1"

                first_line_in_sample = first_lines_sample.splitlines()[0] if first_lines_sample.splitlines() else ""
                if first_line_in_sample.count(";") > first_line_in_sample.count(","):
                    delimiter = ";"
                elif first_line_in_sample.count("\t") > first_line_in_sample.count(","):
                    delimiter = "\t"

                # --- 2. Iterador combinado que actualiza el progreso ---
                async def chunk_iterator_with_progress(f, file_size_bytes=file_size):
                    """
                    Iterador asíncrono que lee el archivo en trozos (chunks) y actualiza
                    la barra de progreso.
                    """
                    nonlocal bytes_processed
                    bytes_processed = 0
                    CHUNK_SIZE = 8192  # 8KB
                    while chunk := await f.read(CHUNK_SIZE):
                        bytes_processed += len(chunk)
                        self.upload_progress = int((bytes_processed / file_size_bytes) * 100)
                        yield chunk

                # --- 3. Iterador de filas CSV a partir de chunks ---
                async def csv_row_iterator(chunk_iter, encoding_str, delimiter_char):
                    """
                    Convierte un iterador de chunks de bytes en un iterador de filas CSV.
                    Maneja líneas que pueden estar divididas entre chunks.
                    """
                    buffer = b""
                    async for chunk in chunk_iter:
                        buffer += chunk
                        while b"\n" in buffer:
                            line_bytes, buffer = buffer.split(b"\n", 1)
                            line_str = line_bytes.decode(encoding_str, errors='ignore').strip()
                            if line_str:
                                yield next(csv.reader([line_str], delimiter=delimiter_char))
                    if buffer:
                        line_str = buffer.decode(encoding_str, errors='ignore').strip()
                        if line_str:
                            yield next(csv.reader([line_str], delimiter=delimiter_char))

                # --- 4. Construcción de iteradores y detección de encabezado ---
                chunk_iter = chunk_iterator_with_progress(file, file_size)
                row_iter = csv_row_iterator(chunk_iter, encoding, delimiter)
                try:
                    first_row = await anext(row_iter)
                    line_number = 1
                except StopAsyncIteration:
                    for event in self._set_final_status("El archivo está vacío.", "warning"):
                        yield event
                    continue

                is_header = any(char.isalpha() for char in "".join(first_row[:3]))

                # --- 5. Procesamiento en lotes con SQL Core ---
                registros_para_insertar = []
                total_cargados = 0

                # Procesar la primera fila si no es encabezado
                if not is_header and any(field.strip() for field in first_row):
                    try:
                        record_dict = self._process_row_to_dict(first_row, line_number)
                        registros_para_insertar.append(record_dict)
                    except InvalidRowError as e:
                        self.upload_error_log.append({
                            "line": line_number,
                            "error": str(e),
                            "row_data": delimiter.join(first_row)
                        })

                # Procesar el resto del archivo
                async for row in row_iter:
                    line_number += 1
                    try:
                        # Salta filas vacías que el iterador de CSV podría producir
                        if not any(field.strip() for field in row):
                            continue
                        record_dict = self._process_row_to_dict(row, line_number)
                        registros_para_insertar.append(record_dict)
                    except InvalidRowError as e:
                        self.upload_error_log.append({
                            "line": line_number,
                            "error": str(e),
                            "row_data": delimiter.join(row)
                        })
                        continue  # Continúa con la siguiente fila

                    # Cuando el lote alcanza el tamaño definido, se inserta en la BD
                    if self.cancel_upload:
                        self.upload_status = "Carga cancelada por el usuario."
                        break # Exit the loop if cancellation is requested

                    if len(registros_para_insertar) >= self.BATCH_SIZE:
                        self.upload_status = f"Insertando lote de {len(registros_para_insertar)} registros... ({self.upload_progress}%)"
                        yield # Actualiza la UI antes de la operación de BD que puede ser bloqueante

                        await rx.run_in_thread(functools.partial(self._batch_insert, registros_para_insertar.copy()))
                        total_cargados += len(registros_para_insertar)
                        registros_para_insertar.clear()

                        self.upload_status = f"Procesando... {total_cargados} registros cargados ({self.upload_progress}%)"
                        yield # Actualiza la UI después de la operación de BD

                # Insertar el lote final, solo si no se ha cancelado
                if registros_para_insertar and not self.cancel_upload:
                    self.upload_status = f"Insertando lote final de {len(registros_para_insertar)} registros... ({self.upload_progress}%)"
                    yield
                    await rx.run_in_thread(functools.partial(self._batch_insert, registros_para_insertar.copy()))
                    total_cargados += len(registros_para_insertar)

                if not self.cancel_upload:
                    if self.upload_error_log:
                        # Generar el contenido del archivo de log de errores
                        error_buffer = io.StringIO()
                        writer = csv.writer(error_buffer)
                        writer.writerow(["line_number", "error_message", "original_row_data"])
                        for err in self.upload_error_log:
                            writer.writerow([err["line"], err["error"], err["row_data"]])
                        self.upload_error_file_content = error_buffer.getvalue()
                        error_buffer.close()

                        message = f"¡Éxito parcial! Se cargaron {total_cargados} registros. Se encontraron {len(self.upload_error_log)} errores."
                        for event in self._set_final_status(message, "warning", close_dialog=False):
                            yield event
                    elif total_cargados == 0:
                        for event in self._set_final_status("No se encontraron registros válidos para cargar.", "warning"):
                            yield event
                    else:
                        for event in self._set_final_status(f"¡Éxito! Se cargaron {total_cargados} registros.", "success", close_dialog=True):
                            yield event
            
            except (csv.Error, OSError, UnicodeDecodeError) as e:
                message = (
                    f"Error fatal en la línea ~{line_number}: {e!s}. "
                    f"Verifique que el delimitador ('{delimiter}') sea correcto y que el archivo no esté corrupto."
                )
                for event in self._set_final_status(message, "error"):
                    yield event
            except (IndexError, ValueError, TypeError, AttributeError, RuntimeError) as e:
                for event in self._set_final_status(f"Error inesperado durante la carga en la línea ~{line_number}: {e!s}", "error"):
                    yield event
            finally:
                self.cancel_upload = False # Ensure flag is reset
                self.uploading = False
                self.upload_progress = 0

    def generar_pdf_persona(self, persona: Persona):
        """Genera un archivo PDF con la ficha individual de la persona consultada."""
        buffer = io.BytesIO()
        pdf_filename = f"Ficha_{persona.cedula}.pdf"

        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor("#1A365D"),
            alignment=1, # Centrado
            spaceAfter=15
        )

        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=20
        )

        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor("#2D3748")
        )

        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#1A202C")
        )

        story = []

        # Encabezado
        story.append(Paragraph("SISTEMA DE CONSULTA - BD_PRUEBA", title_style))
        story.append(Paragraph("FICHA OFICIAL DE CONSULTA CIUDADANA", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3182CE"), spaceAfter=20))

        # Tabla de Datos
        datos = [
            [Paragraph("Nacionalidad (V/E):", label_style), Paragraph(persona.v_e or "", value_style)],
            [Paragraph("Cédula de Identidad:", label_style), Paragraph(str(persona.cedula) if persona.cedula is not None else "", value_style)],
            [Paragraph("Nombres:", label_style), Paragraph(f"{persona.primer_nombre} {persona.segundo_nombre}".strip(), value_style)],
            [Paragraph("Apellidos:", label_style), Paragraph(f"{persona.primer_apellido} {persona.segundo_apellido}".strip(), value_style)],
            [Paragraph("Nombre Completo:", label_style), Paragraph(persona.nombre_completo or "", value_style)],
            [Paragraph("Género:", label_style), Paragraph(persona.genero or "", value_style)],
            [Paragraph("Fecha de Nacimiento:", label_style), Paragraph(str(persona.fecha_nacimiento) if persona.fecha_nacimiento else "", value_style)],
            [Paragraph("Código Estado:", label_style), Paragraph(str(persona.estado) if persona.estado is not None else "", value_style)],
            [Paragraph("Nombre Estado:", label_style), Paragraph(persona.nombre_estado or "", value_style)],
            [Paragraph("Código Municipio:", label_style), Paragraph(str(persona.municipio) if persona.municipio is not None else "", value_style)],
            [Paragraph("Nombre Municipio:", label_style), Paragraph(persona.nombre_municipio or "", value_style)],
            [Paragraph("Código Parroquia:", label_style), Paragraph(str(persona.parroquia) if persona.parroquia is not None else "", value_style)],
            [Paragraph("Código Centro Votación:", label_style), Paragraph(str(persona.codigo_cv) if persona.codigo_cv is not None else "", value_style)],
            [Paragraph("Nombre Centro Votación:", label_style), Paragraph(persona.nombre_cv or "", value_style)],
            [Paragraph("Dirección Centro Votación:", label_style), Paragraph(persona.direccion_cv or "", value_style)],
            [Paragraph("Latitud:", label_style), Paragraph(str(persona.latitud) if persona.latitud is not None else "", value_style)],
            [Paragraph("Longitud:", label_style), Paragraph(str(persona.longitud) if persona.longitud is not None else "", value_style)],
        ]

        t = Table(datos, colWidths=[180, 320])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#A0AEC0")),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ]))

        story.append(t)
        story.append(Spacer(1, 30))

        # Pie de página
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=10))
        story.append(Paragraph("Documento generado automáticamente por el sistema.", subtitle_style))

        doc.build(story)

        # Enviar el PDF desde la memoria al navegador para su descarga
        pdf_data = buffer.getvalue()
        buffer.close()
        return rx.download(data=pdf_data, filename=pdf_filename)
# ==========================================
# 3. COMPONENTES VISUALES Y FRONTEND
# ==========================================

def sortable_header(text: str, column_name: str) -> rx.Component:
    """Crea un encabezado de tabla clickeable para ordenar."""
    return rx.table.column_header_cell(
        rx.link(
            rx.hstack(
                rx.text(text),
                rx.cond(
                    State.sort_column == column_name,
                    rx.icon(
                        tag=rx.cond(State.sort_order == "asc", "arrow-up", "arrow-down"),
                        size=16,
                    ),
                ),
                spacing="2",
                align="center",
            ),
            on_click=lambda: State.set_sort_order(column_name),
        )
    )

def visual_progress_bar() -> rx.Component:
    """Crea una barra de progreso más informativa con texto de porcentaje."""
    return rx.vstack(
        rx.hstack(
            rx.text("Progreso de la carga:", size="2", color_scheme="gray"),
            rx.spacer(),
            rx.text(f"{State.upload_progress}%", size="2", weight="bold"),
            width="100%",
        ),
        rx.progress(
            value=State.upload_progress,
            width="100%",
            size="2",
            color_scheme=rx.cond(State.upload_progress >= 100, "green", "blue"),
            transition="all 0.3s ease-in-out",
        ),
        spacing="1",
        width="100%",
    )

def txt_upload_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button("Carga Masiva (.TXT)", icon="file-text", color_scheme="green"),
        ),
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Cargar Datos desde Archivo TXT"),
                rx.dialog.description("Selecciona el archivo de texto o delimitado por comas."),
                rx.upload(
                    rx.vstack(
                        rx.button("Seleccionar Archivo TXT", icon="upload", variant="soft"),
                        rx.text("O arrastra el archivo aquí"),
                    ),
                    id="txt_upload",
                    accept={"text/plain": [".txt", ".csv"]},
                    border="1px dashed var(--gray-8)",
                    padding="2rem",
                    border_radius="8px",
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Procesar Carga",
                        icon="database",
                        color_scheme="blue",
                        on_click=State.handle_upload(
                            rx.upload_files(
                                upload_id="txt_upload",
                                on_upload_progress=State.handle_upload_progress,
                            )
                        ),
                        is_loading=State.uploading,
                        is_disabled=State.uploading, # Disable if already uploading
                    ),
                    rx.cond(
                        State.uploading,
                        rx.button(
                            "Cancelar Carga",
                            icon="x-circle",
                            color_scheme="red",
                            on_click=State.cancel_current_upload,
                        ),
                    ),
                    rx.dialog.close(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                ),
                rx.cond(
                    State.uploading, visual_progress_bar()
                ),
                rx.cond(
                    State.upload_status != "",
                    rx.vstack(
                        rx.callout(
                            State.upload_status,
                            icon=State.upload_status_icon,
                            color_scheme=State.upload_status_color,
                            opacity=State.upload_status_opacity,
                            transition="opacity 0.5s ease-out",
                        ),
                        rx.cond(
                            State.upload_error_file_content,
                            rx.button(
                                "Descargar Log de Errores",
                                icon="download",
                                color_scheme="orange",
                                on_click=State.download_error_log,
                                margin_top="0.5rem",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                spacing="4",
            )
        ),
        open=State.show_upload_dialog,
        on_open_change=State.set_show_upload_dialog,
    )

def search_view() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading(f"¡Bienvenido, {State.logged_user.username}!", size="8"),
            rx.spacer(),
            txt_upload_dialog(),
            width="100%",
            align="center",
        ),
        rx.grid(
            rx.flex(
                rx.text("Cédula de Identidad", as_="div", size="2", mb="1", weight="bold"),
                rx.input(
                    placeholder="V-12345678",
                    value=State.search_cedula,
                    on_change=State.set_search_cedula,
                    size="3",
                ),
                direction="column",
            ),
            rx.flex(
                rx.text("Primer Nombre", as_="div", size="2", mb="1", weight="bold"),
                rx.input(
                    placeholder="Ej. Juan",
                    value=State.search_primer_nombre,
                    on_change=State.set_search_primer_nombre,
                    size="3",
                ),
                direction="column",
            ),
            rx.flex(
                rx.text("Primer Apellido", as_="div", size="2", mb="1", weight="bold"),
                rx.input(
                    placeholder="Ej. Pérez",
                    value=State.search_primer_apellido,
                    on_change=State.set_search_primer_apellido,
                    size="3",
                ),
                direction="column",
            ),
            columns={"initial": "1", "sm": "3"},
            spacing="3",
            width="100%",
        ),
        rx.hstack(
            rx.button("Buscar", icon="search", size="3", color_scheme="blue", on_click=lambda: State.buscar_persona(new_search=True)),
            rx.cond(
                State.has_search_terms,
                rx.button(
                    "Limpiar",
                    icon="x",
                    size="3",
                    variant="soft",
                    color_scheme="gray",
                    on_click=State.limpiar_busqueda
                ),
            ),
            width="100%",
            spacing="3",
        ),
        rx.divider(),
        rx.cond(
            State.is_loading,
            rx.vstack(
                rx.progress(width="100%"),
                rx.text("Buscando...", size="2", color_scheme="gray"),
                spacing="2",
                width="100%",
                padding_y="4rem",
                align="center",
            ),
            rx.cond(
                State.total_results > 0,
                # Si hay resultados, mostrar la tabla y la paginación
                rx.fragment(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                sortable_header("V/E", "v_e"),
                                sortable_header("Cédula", "cedula"),
                                sortable_header("Nombre Completo", "nombre_completo"),
                                sortable_header("Fecha Nacimiento", "fecha_nacimiento"),
                                sortable_header("Estado", "estado"),
                                rx.table.column_header_cell("Acción / Reporte"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.resultados,
                                lambda p, index: rx.table.row(
                                    rx.table.cell(p.v_e),
                                    rx.table.cell(p.cedula),
                                    rx.table.cell(p.nombre_completo),
                                    rx.table.cell(p.fecha_nacimiento),
                                    rx.table.cell(p.estado),
                                    rx.table.cell(
                                        rx.button(
                                            "Generar PDF",
                                            icon="file-text",
                                            color_scheme="red",
                                            size="2",
                                            variant="soft",
                                            on_click=lambda: State.generar_pdf_persona(p),
                                        )
                                    ),
                                    style=rx.cond(
                                        index % 2 == 0,
                                        {"background_color": "var(--gray-3)"},
                                        {"background_color": "transparent"},
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.hstack(
                        rx.text(
                            f"Página {State.current_page} de {State.total_pages} ({State.total_results} resultados)"
                        ),
                        rx.spacer(),
                        rx.button("Anterior", on_click=State.prev_page, is_disabled=State.current_page <= 1),
                        rx.button("Siguiente", on_click=State.next_page, is_disabled=State.current_page >= State.total_pages),
                        width="100%",
                    ),
                ),
                # Si no hay resultados, mostrar un mensaje (solo después de una búsqueda)
                rx.cond(
                    State.has_search_terms,
                    rx.center(
                        rx.callout(
                            "No se encontró ninguna información para el registro buscado.",
                            icon="info",
                            color_scheme="blue",
                            margin_y="2rem",
                        ),
                        width="100%",
                    )
                )
            )
        ),
        width="100%",
        spacing="5",
        padding_y="2rem",
    )

def delete_user_dialog() -> rx.Component:
    """Diálogo de confirmación para eliminar un usuario."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Confirmar Eliminación"),
            rx.alert_dialog.description(
                "¿Estás seguro de que quieres eliminar al usuario '",
                rx.text(State.deleting_user.username, as_="span", weight="bold"),
                "'? Esta acción no se puede deshacer."
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button("Cancelar", variant="soft", color_scheme="gray"),
                ),
                rx.alert_dialog.action(
                    rx.button("Eliminar Usuario", color_scheme="red", on_click=State.delete_user),
                ),
                spacing="3",
                margin_top="16px",
                justify="end",
            ),
        ),
        open=State.show_delete_user_dialog,
        on_open_change=State.set_show_delete_user_dialog,
    )

def edit_user_dialog() -> rx.Component:
    """Diálogo para editar los detalles de un usuario."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.cond(
                State.editing_user,
                rx.vstack(
                    rx.dialog.title(f"Editando Usuario: {State.editing_user.username}"),
                    rx.dialog.description("Modifica los detalles del usuario y guarda los cambios."),
                    rx.flex(
                        rx.text("Rol:", weight="bold"),
                        rx.select(
                            ["admin", "usuario"],
                            value=State.editing_user.rol,
                            on_change=State.set_editing_user_rol,
                        ),
                        direction="column",
                        spacing="2",
                    ),
                    rx.flex(
                        rx.text("Estado:", weight="bold"),
                        rx.hstack(
                            rx.text("Inactivo"),
                            rx.switch(
                                checked=State.editing_user.activo,
                                on_change=State.set_editing_user_activo,
                            ),
                            rx.text("Activo"),
                            spacing="2",
                            align="center",
                        ),
                        direction="column",
                        spacing="2",
                    ),
                    rx.flex(
                        rx.text("Nueva Contraseña:", weight="bold"),
                        rx.input(
                            placeholder="Dejar en blanco para no cambiar",
                            type="password",
                            on_change=State.set_new_password_input,
                        ),
                        direction="column",
                        spacing="2",
                    ),
                    rx.flex(
                        rx.button(
                            "Cancelar",
                            variant="soft",
                            color_scheme="gray",
                            on_click=lambda: State.set_show_edit_user_dialog(False),
                        ),
                        rx.button(
                            "Guardar Cambios",
                            on_click=State.save_user_changes,
                        ),
                        spacing="3",
                        margin_top="16px",
                        justify="end",
                    ),
                    spacing="4",
                ),
            )
        ),
        open=State.show_edit_user_dialog,
        on_open_change=State.set_show_edit_user_dialog,
    )

def admin_view() -> rx.Component:
    """Vista para administrar usuarios (crear y listar)."""
    return rx.vstack(
        rx.heading("Administración de Usuarios", size="8", margin_bottom="1rem"),
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.heading("Crear Nuevo Usuario", size="5"),
                    rx.text("Nombre de Usuario", margin_top="1rem"),
                    rx.input(
                        placeholder="ej. juanperez",
                        value=State.new_user_username,
                        on_change=State.set_new_user_username,
                        width="100%",
                    ),
                    rx.text("Contraseña", margin_top="1rem"),
                    rx.input(
                        placeholder="Contraseña segura",
                        type="password",
                        value=State.new_user_password,
                        on_change=State.set_new_user_password,
                        width="100%",
                    ),
                    rx.text("Rol", margin_top="1rem"),
                    rx.select(
                        ["usuario", "admin"],
                        value=State.new_user_rol,
                        on_change=State.set_new_user_rol,
                        width="100%",
                    ),
                    rx.button(
                        "Crear Usuario",
                        on_click=State.crear_nuevo_usuario,
                        width="100%",
                        margin_top="1.5rem",
                    ),
                    rx.cond(
                        State.form_message != "",
                        rx.callout(
                            State.form_message,
                            icon=rx.cond(State.form_message_color == "red", "triangle_alert", "check_circle"),
                            color_scheme=State.form_message_color,
                            role="alert",
                            margin_top="1rem",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                )
            ),
            rx.vstack(
                rx.hstack(
                    rx.heading("Usuarios Existentes", size="5"),
                    rx.spacer(),
                    rx.button("Recargar", icon="refresh-cw", on_click=State.load_users, variant="soft"),
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Username"),
                            rx.table.column_header_cell("Rol"),
                            rx.table.column_header_cell("Estado"),
                            rx.table.column_header_cell("Acciones"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            State.users,
                            lambda user: rx.table.row(
                                rx.table.cell(user.username),
                                rx.table.cell(user.rol),
                                rx.table.cell(
                                    rx.badge(
                                        rx.cond(user.activo, "Activo", "Inactivo"),
                                        color_scheme=rx.cond(user.activo, "green", "red"),
                                    )
                                ),
                                rx.table.cell(
                                    rx.hstack(
                                        rx.button(
                                            "Editar",
                                            icon="pencil",
                                            on_click=lambda: State.start_edit_user(user),
                                            size="2",
                                        ),
                                        rx.button(
                                            "Eliminar",
                                            icon="trash-2",
                                            color_scheme="red",
                                            on_click=lambda: State.start_delete_user(user),
                                            is_disabled=user.username == "admin",
                                            size="2",
                                        ),
                                        spacing="2",
                                    ),
                                ),
                            )
                        )
                    ),
                ),
                spacing="3",
                width="100%",
            ),
            columns={"initial": "1", "md": "2"},
            spacing="5",
            width="100%",
        ),
        edit_user_dialog(),
        delete_user_dialog(),
        width="100%",
        spacing="5",
        padding_y="2rem",
    )

def navbar() -> rx.Component:
    return rx.hstack(
        rx.drawer.root(
            rx.drawer.trigger(rx.button(rx.icon("menu"), variant="soft")),
            rx.drawer.overlay(
                z_index="999",
                transition="opacity 0.3s ease",
                style={"background_color": "rgba(0, 0, 0, 0.5)"},
            ),
            rx.drawer.content(
                rx.vstack(
                    rx.drawer.close(rx.button(rx.icon("x"), variant="soft", align_self="flex-end")),
                    rx.heading("Menú", size="6"),
                    rx.divider(),
                    rx.drawer.close(
                        rx.button(
                            rx.hstack(rx.icon("search"), rx.text("Búsqueda")),
                            on_click=lambda: State.set_dashboard_view("search"),
                            variant="ghost",
                            width="100%",
                            justify_content="flex-start",
                        ),
                        as_child=True,
                    ),
                    rx.cond(
                        State.logged_user.rol == "admin",
                        rx.drawer.close(
                            rx.button(
                                rx.hstack(rx.icon("settings"), rx.text("Administrar Usuarios")),
                                on_click=lambda: State.set_dashboard_view("admin_users"),
                                variant="ghost",
                                width="100%",
                                justify_content="flex-start",
                            ),
                            as_child=True,
                        ),
                    ),
                    rx.spacer(),
                    rx.drawer.close(
                        rx.button(
                            rx.hstack(rx.icon("log-out"), rx.text("Cerrar Sesión")),
                            on_click=State.logout,
                            variant="soft",
                            color_scheme="red",
                            width="100%",
                            justify_content="flex-start",
                        ),
                        as_child=True,
                    ),
                    spacing="4",
                    padding="1rem",
                    height="100%",
                ),
                width="250px",
                z_index="9999",
                transition="transform 0.3s ease",
                background_color="var(--gray-2)",
            ),
            direction="left",
            open=State.show_sidebar,
            on_open_change=State.toggle_sidebar,
        ),
        rx.heading("BD_Prueba", size="6", color="white"),
        rx.spacer(),
        rx.color_mode.button(),
        rx.menu.root(
            rx.menu.trigger(
                rx.button(
                    rx.icon("user"),
                    rx.text(State.logged_user.username),
                    variant="soft",
                    color_scheme="indigo",
                )
            ),
            rx.menu.content(
                rx.menu.item("Perfil", icon="user-check"),
                rx.menu.item("Ajustes", icon="settings"),
                rx.menu.separator(),
                rx.menu.item(
                    "Cerrar Sesión",
                    icon="log-out",
                    on_click=State.logout,
                    color="red",
                ),
            ),
        ),
        width="100%",
        padding="1rem",
        border_bottom="1px solid var(--gray-5)",
        align="center",
        # Posicionamiento para que no se superponga con el contenido al hacer scroll
        position="fixed",
        top="0",
        z_index="100",
        background_color="#1A365D",
    )

def login_view() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Iniciar Sesión", size="7", width="100%", text_align="center"),
                rx.cond(
                    State.error_msg != "",
                    rx.callout(State.error_msg, icon="triangle_alert", color_scheme="red", role="alert"),
                ),
                rx.text("Usuario"),
                rx.input(placeholder="Ingrese su usuario", on_change=State.set_input_user, width="100%"),
                rx.text("Contraseña"),
                rx.input(type="password", placeholder="••••••••", on_change=State.set_input_pass, width="100%"),
                rx.button("Ingresar", icon="key-round", width="100%", color_scheme="blue", on_click=State.login),
                spacing="4",
                width="100%",
            ),
            width=["90%", "400px"],
            padding="2rem",
        ),
        height="100vh",
    )

def main_dashboard() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.cond(
                State.current_dashboard_view == "search",
                search_view(),
                admin_view(),
            ),
            padding_x=["1rem", "2rem", "4rem"],
            padding_top="5rem",  # Espacio para la navbar fija
            width="100%",
        ),
        rx.toast.provider(),
        width="100%",
    )


def index() -> rx.Component:
    return rx.fragment(
        rx.cond(State.logged_user, main_dashboard(), login_view()),
        rx.toast.provider(),
    )


app = rx.App()
app.add_page(
    index,
    title="BD_Prueba - Sistema de Consultas",
    on_load=State.crear_usuario_inicial,
)