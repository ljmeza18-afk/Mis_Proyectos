"""Por Leobaldo Meza."""
import asyncio
import csv
import datetime
import functools
import hashlib
import hmac
import io
import json
import os
import re
import secrets
from urllib.parse import quote

import qrcode  # type: ignore[reportMissingImports]
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


def hash_password(password: str) -> str:
    """Genera un hash PBKDF2 portable sin guardar contraseñas en claro."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_password: str) -> bool:
    """Verifica hashes nuevos y permite migrar usuarios antiguos en claro."""
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password, stored_password)
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

try:
    from reportlab.lib import colors  # type: ignore[reportMissingImports]
    from reportlab.lib.pagesizes import letter  # type: ignore[reportMissingImports]
    from reportlab.lib.styles import (  # type: ignore[reportMissingImports]
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.platypus import (  # type: ignore[reportMissingImports]
        Image,
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.units import inch  # type: ignore[reportMissingImports]
    from reportlab.lib.utils import ImageReader  # type: ignore[reportMissingImports]
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

class Usuario(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    username: str = sqlmodel.Field(unique=True, index=True)
    password: str
    rol: str = "admin"  # 'admin' o 'usuario'
    activo: bool = True
    can_consultar: bool = sqlmodel.Field(default=True)
    can_imprimir: bool = sqlmodel.Field(default=True)


class Persona(sqlmodel.SQLModel, table=True):
    id: int | None = sqlmodel.Field(default=None, primary_key=True)
    v_e: str = ""
    cedula: int = sqlmodel.Field(index=True)
    primer_apellido: str = sqlmodel.Field(index=True)
    segundo_apellido: str = ""
    primer_nombre: str = sqlmodel.Field(index=True)
    segundo_nombre: str = ""
    nombre_completo: str = sqlmodel.Field(index=True)
    genero: str = ""
    fecha_nacimiento: datetime.date | None = None
    estado: int | None = None
    municipio: int | None = None
    parroquia: int | None = None
    codigo_cv: int | None = None
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
    is_logged_in: bool = False
    logged_user_id: int | None = None
    logged_user_username: str = ""
    logged_user_rol: str = ""
    logged_user_can_consultar: bool = True
    logged_user_can_imprimir: bool = True

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
    resultados: list[dict] = []
    is_loading: bool = False
    sort_column: str = "nombre_completo"
    sort_order: str = "asc"

    # Paginación
    current_page: int = 1
    page_size: int = 10
    total_results: int = 0

    # Búsqueda por municipio y mapa
    municipality_state: str = "Nueva Esparta"
    municipality_filters: list[dict[str, str]] = [{"municipio": "", "nombre_cv": ""}]
    municipality_cv_options: list[list[str]] = [[]]
    municipality_selected_cvs: list[list[str]] = [[]]
    municipality_results: list[dict] = []
    municipality_total: int = 0
    municipality_is_loading: bool = False
    municipality_detail_results: list[dict] = []
    municipality_detail_total: int = 0
    municipality_detail_is_loading: bool = False
    municipality_detail_prompt: bool = False
    municipality_detail_page: int = 1
    municipality_detail_page_size: int = 10

    # Admin Users
    users: list[dict] = []
    show_edit_user_dialog: bool = False
    edit_user_id: int | None = None
    edit_user_username: str = ""
    edit_user_rol: str = "usuario"
    edit_user_activo: bool = True
    edit_user_can_consultar: bool = True
    edit_user_can_imprimir: bool = True
    edit_password_input: str = ""

    show_delete_user_dialog: bool = False
    deleting_user_id: int | None = None
    deleting_user_username: str = ""

    new_user_username: str = ""
    new_user_password: str = ""
    new_user_rol: str = "usuario"
    new_user_can_consultar: bool = True
    new_user_can_imprimir: bool = True

    form_message: str = ""
    form_message_color: str = "red"

    # Constantes de la clase
    BATCH_SIZE = 10000  # Lote para la carga masiva

    # Estado de Carga Masiva
    upload_status: str = ""
    uploading: bool = False
    upload_progress: int = 0
    cancel_upload: bool = False
    upload_error_log: list[dict] = []
    upload_error_file_content: str | None = None
    upload_total_cargados: int = 0

    upload_status_opacity: float = 0.0
    show_upload_dialog: bool = False

    @rx.var
    def is_admin(self) -> bool:
        """Indica si el usuario conectado tiene rol admin."""
        return self.logged_user_rol == "admin"

    @rx.var
    def upload_status_icon(self) -> str:
        """Devuelve el icono adecuado según el estado de la carga."""
        if self.upload_status.startswith("¡Éxito!"):
            return "check-circle"
        if self.upload_status.startswith("Error") or "error" in self.upload_status.lower():
            return "triangle-alert"
        return "info"

    @rx.var
    def upload_status_color(self) -> str:
        """Devuelve el color adecuado según el estado de la carga."""
        if self.upload_status.startswith("¡Éxito!"):
            return "green"
        if self.upload_status.startswith("Error") or "error" in self.upload_status.lower():
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

    @rx.var
    def has_municipality_filters(self) -> bool:
        return any(
            item["municipio"].strip() or self.municipality_selected_cvs[index]
            for index, item in enumerate(self.municipality_filters)
        )

    @rx.var
    def municipality_detail_total_pages(self) -> int:
        if self.municipality_detail_total == 0 or self.municipality_detail_page_size == 0:
            return 1
        return (self.municipality_detail_total + self.municipality_detail_page_size - 1) // self.municipality_detail_page_size

    @rx.var
    def municipality_detail_display(self) -> list[dict]:
        return self.municipality_detail_results

    @rx.var
    def municipality_detail_page_size_label(self) -> str:
        return "all" if self.municipality_detail_page_size == 0 else str(self.municipality_detail_page_size)

    # Setters explícitos
    def set_search_query(self, value: str):
        self.search_query = value

    def set_show_upload_dialog(self, value: bool):
        self.show_upload_dialog = value
        if value:
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

    def set_municipality_query(self, value: str):
        self.set_municipality_filter(0, "municipio", value)

    def set_municipality_filter(self, index: int, field: str, value: str):
        if 0 <= index < len(self.municipality_filters) and field == "municipio":
            filters = [dict(item) for item in self.municipality_filters]
            filters[index]["municipio"] = value
            filters[index]["nombre_cv"] = ""
            self.municipality_filters = filters
            with rx.session() as session:
                centers = session.exec(
                    sqlmodel.select(Persona.nombre_cv)
                    .where(
                        sqlmodel.and_(
                            sqlmodel.func.trim(sqlmodel.func.lower(Persona.nombre_estado))
                            == self.municipality_state.strip().lower(),
                            sqlmodel.func.trim(sqlmodel.func.lower(Persona.nombre_municipio)) == value.strip().lower(),
                            sqlmodel.func.trim(Persona.nombre_cv) != "",
                        )
                    )
                    .distinct()
                    .order_by(Persona.nombre_cv)
                ).all()
            options = [*self.municipality_cv_options]
            selected = [*self.municipality_selected_cvs]
            options[index] = list(centers)
            selected[index] = []
            self.municipality_cv_options = options
            self.municipality_selected_cvs = selected

    def toggle_municipality_cv(self, index: int, name: str, checked: bool):
        if not 0 <= index < len(self.municipality_selected_cvs):
            return
        selected = [list(item) for item in self.municipality_selected_cvs]
        if checked and name not in selected[index]:
            selected[index].append(name)
        elif not checked and name in selected[index]:
            selected[index].remove(name)
        self.municipality_selected_cvs = selected

    def add_municipality_filter(self):
        self.municipality_filters = [*self.municipality_filters, {"municipio": "", "nombre_cv": ""}]
        self.municipality_cv_options = [*self.municipality_cv_options, []]
        self.municipality_selected_cvs = [*self.municipality_selected_cvs, []]

    def set_municipality_detail_page_size(self, value: str):
        self.municipality_detail_page_size = 0 if value == "all" else int(value)
        self.municipality_detail_page = 1
        self._load_municipality_detail_page()

    def next_municipality_detail_page(self):
        if self.municipality_detail_page < self.municipality_detail_total_pages:
            self.municipality_detail_page += 1
            self._load_municipality_detail_page()

    def previous_municipality_detail_page(self):
        if self.municipality_detail_page > 1:
            self.municipality_detail_page -= 1
            self._load_municipality_detail_page()

    def remove_municipality_filter(self, index: int):
        if len(self.municipality_filters) > 1:
            self.municipality_filters = [
                dict(item) for item_index, item in enumerate(self.municipality_filters) if item_index != index
            ]
            self.municipality_cv_options = [
                item for item_index, item in enumerate(self.municipality_cv_options) if item_index != index
            ]
            self.municipality_selected_cvs = [
                item for item_index, item in enumerate(self.municipality_selected_cvs) if item_index != index
            ]

    def set_municipality_state(self, value: str):
        self.municipality_state = value

    @rx.var
    def search_map_url(self) -> str:
        data = json.dumps(self.resultados, ensure_ascii=False)
        return f"/mapa.html?data={quote(data)}"

    @rx.var
    def municipality_map_url(self) -> str:
        data = json.dumps(self.municipality_results, ensure_ascii=False)
        return f"/mapa.html?mode=municipality&data={quote(data)}"

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

    def set_new_user_can_consultar(self, value: bool):
        self.new_user_can_consultar = value

    def set_new_user_can_imprimir(self, value: bool):
        self.new_user_can_imprimir = value

    def set_edit_user_rol(self, rol: str):
        self.edit_user_rol = rol

    def set_edit_user_activo(self, activo: bool):
        self.edit_user_activo = activo

    def set_edit_user_can_consultar(self, can_consultar: bool):
        self.edit_user_can_consultar = can_consultar

    def set_edit_user_can_imprimir(self, can_imprimir: bool):
        self.edit_user_can_imprimir = can_imprimir

    def set_edit_password_input(self, password: str):
        self.edit_password_input = password

    def crear_usuario_inicial(self):
        """Crea el usuario administrador inicial si no existe."""
        try:
            initial_password = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123")
            with rx.session() as session:
                admin_existente = session.exec(
                    sqlmodel.select(Usuario).where(Usuario.username == "admin")
                ).first()
                if not admin_existente:
                    admin = Usuario(
                        username="admin",
                        password=hash_password(initial_password),
                        rol="admin",
                        activo=True,
                        can_consultar=True,
                        can_imprimir=True,
                    )
                    session.add(admin)
                    session.commit()
        except Exception:
            pass

    def toggle_sidebar(self):
        self.show_sidebar = not self.show_sidebar

    def set_dashboard_view(self, view_name: str):
        self.current_dashboard_view = view_name
        if view_name == "admin_users":
            self.load_users()

    def login(self):
        self.error_msg = ""
        user_input = self.input_user.strip()
        pass_input = self.input_pass
        if not user_input or not pass_input:
            self.error_msg = "Por favor ingrese usuario y contraseña."
            return

        with rx.session() as session:
            user = session.exec(
                sqlmodel.select(Usuario).where(Usuario.username == user_input)
            ).first()
            if not user or not verify_password(pass_input, user.password):
                self.error_msg = "Usuario o contraseña incorrectos."
                return

            if not user.password.startswith("pbkdf2_sha256$"):
                user.password = hash_password(pass_input)
                session.add(user)
                session.commit()

            if not user.activo:
                self.error_msg = "El usuario se encuentra inactivo. Comuníquese con el administrador."
                return

            self.logged_user_id = user.id
            self.logged_user_username = user.username
            self.logged_user_rol = user.rol
            self.logged_user_can_consultar = user.can_consultar
            self.logged_user_can_imprimir = user.can_imprimir
            self.is_logged_in = True
            self.input_pass = ""
            self.error_msg = ""

    def handle_login_key_down(self, key: str):
        """Maneja la tecla Enter en el formulario de login."""
        if key == "Enter":
            return State.login

    def handle_search_key_down(self, key: str):
        """Maneja la tecla Enter en los campos de búsqueda."""
        if key == "Enter":
            return State.buscar_persona(new_search=True)

    def handle_municipality_key_down(self, key: str):
        if key == "Enter":
            return State.buscar_municipio

    def logout(self):
        self.is_logged_in = False
        self.logged_user_id = None
        self.logged_user_username = ""
        self.logged_user_rol = ""
        self.logged_user_can_consultar = True
        self.logged_user_can_imprimir = True
        self.current_dashboard_view = "search"

    def load_users(self):
        with rx.session() as session:
            db_users = session.exec(sqlmodel.select(Usuario)).all()
            self.users = [
                {
                    "id": u.id,
                    "username": u.username,
                    "rol": u.rol,
                    "activo": u.activo,
                    "can_consultar": u.can_consultar,
                    "can_imprimir": u.can_imprimir,
                }
                for u in db_users
            ]

    def set_show_edit_user_dialog(self, show: bool):
        """Controla la visibilidad del diálogo de edición."""
        self.show_edit_user_dialog = show
        if not show:
            self.edit_user_id = None
            self.edit_user_username = ""
            self.edit_password_input = ""
            self.load_users()

    def start_edit_user(self, user: dict):
        """Prepara el diálogo para editar un usuario."""
        self.edit_user_id = user.get("id")
        self.edit_user_username = user.get("username", "")
        self.edit_user_rol = user.get("rol", "usuario")
        self.edit_user_activo = user.get("activo", True)
        self.edit_user_can_consultar = user.get("can_consultar", True)
        self.edit_user_can_imprimir = user.get("can_imprimir", True)
        self.edit_password_input = ""
        self.show_edit_user_dialog = True

    def save_user_changes(self):
        """Guarda los cambios del usuario editado en la base de datos."""
        if not self.edit_user_id:
            return
        with rx.session() as session:
            db_user = session.get(Usuario, self.edit_user_id)
            if db_user:
                db_user.rol = self.edit_user_rol
                db_user.activo = self.edit_user_activo
                db_user.can_consultar = self.edit_user_can_consultar
                db_user.can_imprimir = self.edit_user_can_imprimir
                if self.edit_password_input.strip():
                    db_user.password = hash_password(self.edit_password_input.strip())
                session.add(db_user)
                session.commit()
                if self.is_logged_in and self.logged_user_id == db_user.id:
                    self.logged_user_rol = db_user.rol
                    self.logged_user_can_consultar = db_user.can_consultar
                    self.logged_user_can_imprimir = db_user.can_imprimir

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
                password=hash_password(self.new_user_password.strip()),
                rol=self.new_user_rol,
                activo=True,
                can_consultar=self.new_user_can_consultar,
                can_imprimir=self.new_user_can_imprimir,
            )
            session.add(new_user)
            session.commit()
            self.form_message = f"Usuario '{self.new_user_username.strip()}' creado con éxito."
            self.form_message_color = "green"
            self.new_user_can_consultar = True
            self.new_user_can_imprimir = True
            self.new_user_username = ""
            self.new_user_password = ""
            self.limpiar_busqueda()
            self.load_users()

    def start_delete_user(self, user: dict):
        """Prepara el diálogo para eliminar un usuario."""
        self.deleting_user_id = user.get("id")
        self.deleting_user_username = user.get("username", "")
        self.show_delete_user_dialog = True

    def set_show_delete_user_dialog(self, show: bool):
        """Controla la visibilidad del diálogo de eliminación."""
        self.show_delete_user_dialog = show
        if not show:
            self.deleting_user_id = None
            self.deleting_user_username = ""

    def delete_user(self):
        """Elimina el usuario seleccionado."""
        if not self.deleting_user_id or self.deleting_user_username == "admin":
            self.set_show_delete_user_dialog(False)
            return

        if self.is_logged_in and self.logged_user_id == self.deleting_user_id:
            self.set_show_delete_user_dialog(False)
            return rx.toast.error("No puedes eliminar la cuenta con la que has iniciado sesión actualmente.")

        with rx.session() as session:
            user_to_delete = session.get(Usuario, self.deleting_user_id)
            if user_to_delete:
                session.delete(user_to_delete)
                session.commit()

        self.set_show_delete_user_dialog(False)
        self.load_users()

    def clear_upload_status(self):
        """Limpia el mensaje de estado de carga."""
        self.upload_status_opacity = 0.0
        self.upload_status = ""

    def cancel_current_upload(self):
        """Cancela la carga de archivos en progreso."""
        self.cancel_upload = True
        self.upload_progress = 0
        self.uploading = False
        self.upload_status = "Carga cancelada por el usuario."
        return rx.toast.info("Carga cancelada por el usuario.")

    def download_error_log(self):
        """Descarga el log de errores de la última carga masiva."""
        if not self.upload_error_file_content:
            return rx.toast.error("No hay un log de errores para descargar.")

        return rx.download(
            data=self.upload_error_file_content.encode("utf-8-sig"),  # Use utf-8-sig for better Excel compatibility
            filename=f"upload_errors_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
        )
    
    @rx.var
    def total_pages(self) -> int:
        """Calcula el número total de páginas."""
        if self.total_results == 0:
            return 1
        return (self.total_results + self.page_size - 1) // self.page_size

    @rx.var
    def resultados_display(self) -> list[dict]:
        """Prepara los resultados para ser mostrados en la tabla con el formato deseado."""
        return self.resultados

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

    def _build_search_query(self):
        """Construye la consulta de búsqueda base a partir de los términos del estado."""
        search_cedula_term = self.search_cedula.strip()
        search_nombre_term = self.search_primer_nombre.strip().lower()
        search_apellido_term = self.search_primer_apellido.strip().lower()

        conditions = []

        if search_cedula_term:
            # Limpiar puntos y comas de formato de cédula (ej: 12.345.678 -> 12345678)
            cleaned_cedula = re.sub(r"[\.,]", "", search_cedula_term)
            cedula_match = re.match(r"^(V|E|v|e)?[\s-]*(\d{1,9})$", cleaned_cedula)
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
            return None
        return sqlmodel.and_(*conditions)

    def buscar_persona(self, new_search: bool = False):
        """Realiza la búsqueda con paginación y muestra un indicador de carga."""
        self.is_loading = True
        if new_search:
            self.current_page = 1
        yield
        try:
            with rx.session() as session:
                final_condition = self._build_search_query()
                if final_condition is None:
                    self.resultados, self.total_results = [], 0
                    return

                base_query = sqlmodel.select(Persona).where(final_condition)

                # Obtener conteo total en nueva búsqueda o cuando el conteo actual sea 0
                if new_search or self.total_results == 0:
                    count_query = sqlmodel.select(sqlmodel.func.count(Persona.id)).where(final_condition)
                    self.total_results = session.exec(count_query).one()

                # Aplicar ordenamiento seguro
                sort_attribute = getattr(Persona, self.sort_column, Persona.nombre_completo)
                order = sqlmodel.asc if self.sort_order == "asc" else sqlmodel.desc
                sorted_query = base_query.order_by(order(sort_attribute))

                # Aplicar paginación
                offset = (self.current_page - 1) * self.page_size
                paginated_query = sorted_query.offset(offset).limit(self.page_size)
                personas = session.exec(paginated_query).all()
                self.resultados = [
                    {
                        "id": p.id,
                        "v_e": p.v_e,
                        "cedula": p.cedula,
                        "primer_apellido": p.primer_apellido,
                        "segundo_apellido": p.segundo_apellido,
                        "primer_nombre": p.primer_nombre,
                        "segundo_nombre": p.segundo_nombre,
                        "nombre_completo": p.nombre_completo,
                        "genero": p.genero,
                        "fecha_nacimiento": p.fecha_nacimiento.strftime("%d-%m-%Y") if p.fecha_nacimiento else "",
                        "estado": p.estado,
                        "municipio": p.municipio,
                        "parroquia": p.parroquia,
                        "codigo_cv": p.codigo_cv,
                        "nombre_estado": p.nombre_estado,
                        "nombre_municipio": p.nombre_municipio,
                        "nombre_cv": p.nombre_cv,
                        "direccion_cv": p.direccion_cv,
                        "latitud": float(p.latitud) if p.latitud is not None else None,
                        "longitud": float(p.longitud) if p.longitud is not None else None,
                    }
                    for p in personas
                ]
        finally:
            self.is_loading = False

    def buscar_municipio(self):
        """Busca centros de votación de una o varias filas municipales."""
        self.municipality_is_loading = True
        self.municipality_detail_prompt = False
        self.municipality_detail_results = []
        self.municipality_detail_total = 0
        try:
            active_indices = [
                index
                for index, item in enumerate(self.municipality_filters)
                if item["municipio"].strip() or self.municipality_selected_cvs[index]
            ]
            if not active_indices:
                self.municipality_results = []
                self.municipality_total = 0
                return

            with rx.session() as session:
                municipality_condition = self._build_municipality_condition(active_indices)
                personas = session.exec(
                    sqlmodel.select(Persona)
                    .where(municipality_condition)
                    # PostgreSQL devuelve una sola persona representativa por centro.
                    .distinct(Persona.nombre_cv)
                    .order_by(Persona.nombre_cv, Persona.id)
                ).all()
                self.municipality_results = [
                    {
                        "id": p.id,
                        "v_e": p.v_e,
                        "cedula": p.cedula,
                        "nombre_completo": p.nombre_completo,
                        "primer_nombre": p.primer_nombre,
                        "segundo_nombre": p.segundo_nombre,
                        "primer_apellido": p.primer_apellido,
                        "segundo_apellido": p.segundo_apellido,
                        "fecha_nacimiento": p.fecha_nacimiento.strftime("%d-%m-%Y") if p.fecha_nacimiento else "",
                        "genero": p.genero,
                        "estado": p.estado,
                        "nombre_estado": p.nombre_estado,
                        "municipio": p.municipio,
                        "nombre_municipio": p.nombre_municipio,
                        "parroquia": p.parroquia,
                        "codigo_cv": p.codigo_cv,
                        "nombre_cv": p.nombre_cv,
                        "direccion_cv": p.direccion_cv,
                        "latitud": float(p.latitud) if p.latitud is not None else None,
                        "longitud": float(p.longitud) if p.longitud is not None else None,
                    }
                    for p in personas
                ]
                self.municipality_total = len(self.municipality_results)
                self.municipality_detail_prompt = self.municipality_total > 0
        finally:
            self.municipality_is_loading = False

    def _build_municipality_condition(self, active_indices: list[int]):
        state_condition = sqlmodel.func.trim(sqlmodel.func.lower(Persona.nombre_estado)) == self.municipality_state.strip().lower()
        filter_conditions = []
        for index in active_indices:
            item = self.municipality_filters[index]
            row_conditions = []
            if item["municipio"].strip():
                row_conditions.append(
                    sqlmodel.func.trim(sqlmodel.func.lower(Persona.nombre_municipio))
                    == item["municipio"].strip().lower()
                )
            if self.municipality_selected_cvs[index]:
                row_conditions.append(
                    sqlmodel.func.trim(Persona.nombre_cv).in_(
                        [center.strip() for center in self.municipality_selected_cvs[index]]
                    )
                )
            filter_conditions.append(sqlmodel.and_(*row_conditions))
        return sqlmodel.and_(state_condition, sqlmodel.or_(*filter_conditions))

    @staticmethod
    def _persona_to_dict(persona: Persona) -> dict:
        return {
            "id": persona.id,
            "v_e": persona.v_e,
            "cedula": persona.cedula,
            "nombre_completo": persona.nombre_completo,
            "primer_nombre": persona.primer_nombre,
            "segundo_nombre": persona.segundo_nombre,
            "primer_apellido": persona.primer_apellido,
            "segundo_apellido": persona.segundo_apellido,
            "fecha_nacimiento": persona.fecha_nacimiento.strftime("%d-%m-%Y") if persona.fecha_nacimiento else "",
            "genero": persona.genero,
            "estado": persona.estado,
            "nombre_estado": persona.nombre_estado,
            "municipio": persona.municipio,
            "nombre_municipio": persona.nombre_municipio,
            "parroquia": persona.parroquia,
            "codigo_cv": persona.codigo_cv,
            "nombre_cv": persona.nombre_cv,
            "direccion_cv": persona.direccion_cv,
            "latitud": float(persona.latitud) if persona.latitud is not None else None,
            "longitud": float(persona.longitud) if persona.longitud is not None else None,
        }

    def _active_municipality_indices(self) -> list[int]:
        return [
            index for index, item in enumerate(self.municipality_filters)
            if item["municipio"].strip() or self.municipality_selected_cvs[index]
        ]

    def _load_municipality_detail_page(self):
        """Carga solo la página solicitada desde PostgreSQL."""
        active_indices = self._active_municipality_indices()
        if not active_indices:
            self.municipality_detail_results = []
            self.municipality_detail_total = 0
            return
        with rx.session() as session:
            condition = self._build_municipality_condition(active_indices)
            count_query = sqlmodel.select(sqlmodel.func.count(Persona.id)).where(condition)
            self.municipality_detail_total = session.exec(count_query).one()
            detail_query = (
                sqlmodel.select(Persona)
                .where(condition)
                .order_by(Persona.nombre_municipio, Persona.nombre_cv, Persona.id)
            )
            if self.municipality_detail_page_size:
                offset = (self.municipality_detail_page - 1) * self.municipality_detail_page_size
                detail_query = detail_query.offset(offset).limit(self.municipality_detail_page_size)
            personas = session.exec(detail_query).all()
            self.municipality_detail_results = [self._persona_to_dict(persona) for persona in personas]

    def buscar_detalle_municipio(self):
        """Inicia la tabla detallada bajo demanda, paginada en PostgreSQL."""
        active_indices = [
            index for index, item in enumerate(self.municipality_filters)
            if item["municipio"].strip() or self.municipality_selected_cvs[index]
        ]
        if not active_indices:
            return
        self.municipality_detail_is_loading = True
        try:
            self.municipality_detail_page = 1
            self._load_municipality_detail_page()
            self.municipality_detail_prompt = False
        finally:
            self.municipality_detail_is_loading = False

    def rechazar_detalle_municipio(self):
        """Limpia el mapa y los filtros para iniciar una nueva consulta."""
        self.municipality_results = []
        self.municipality_total = 0
        self.municipality_detail_results = []
        self.municipality_detail_total = 0
        self.municipality_detail_page = 1
        self.municipality_detail_prompt = False
        self.limpiar_municipio()

    def exportar_detalle_municipio_csv(self):
        """Descarga todos los registros del detalle municipal, no solo la página actual."""
        if not self.municipality_detail_total:
            return rx.toast.warning("No hay resultados detallados para exportar.")

        headers = [
            "v_e", "cedula", "nombre_completo", "primer_nombre", "segundo_nombre",
            "primer_apellido", "segundo_apellido", "fecha_nacimiento", "genero",
            "estado", "nombre_estado", "municipio", "nombre_municipio", "parroquia",
            "codigo_cv", "nombre_cv", "direccion_cv", "latitud", "longitud",
        ]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        active_indices = self._active_municipality_indices()
        with rx.session() as session:
            query = (
                sqlmodel.select(Persona)
                .where(self._build_municipality_condition(active_indices))
                .order_by(Persona.nombre_municipio, Persona.nombre_cv, Persona.id)
                .execution_options(yield_per=5000)
            )
            for persona in session.exec(query):
                result = self._persona_to_dict(persona)
                writer.writerow([
                    result.get(header, "") if result.get(header) is not None else ""
                    for header in headers
                ])

        csv_data = output.getvalue().encode("utf-8-sig")
        output.close()
        filename = (
            "detalle_municipal_"
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        )
        return rx.download(data=csv_data, filename=filename)

    def limpiar_busqueda(self):
        """Limpia el campo de búsqueda y los resultados."""
        self.search_cedula = ""
        self.search_primer_nombre = ""
        self.search_primer_apellido = ""
        self.resultados = []
        self.total_results = 0
        self.current_page = 1

    def limpiar_municipio(self):
        self.municipality_filters = [{"municipio": "", "nombre_cv": ""}]
        self.municipality_cv_options = [[]]
        self.municipality_selected_cvs = [[]]
        self.municipality_results = []
        self.municipality_total = 0

    def exportar_resultados_csv(self):
        """Exporta los resultados de la búsqueda actual a un archivo CSV."""
        if not self.has_search_terms or self.total_results == 0:
            return rx.toast.warning("No hay resultados para exportar. Realice una búsqueda primero.")

        with rx.session() as session:
            final_condition = self._build_search_query()
            if final_condition is None:
                return rx.toast.warning("No hay criterios de búsqueda para exportar.")

            # Query para obtener todos los resultados, ordenados como en la vista
            sort_attribute = getattr(Persona, self.sort_column, Persona.nombre_completo)
            order = sqlmodel.asc if self.sort_order == "asc" else sqlmodel.desc
            full_query = sqlmodel.select(Persona).where(final_condition).order_by(order(sort_attribute))

            all_results = session.exec(full_query).all()

        # Generar el archivo CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)

        # Escribir encabezados
        headers = [
            "v_e", "cedula", "primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido",
            "nombre_completo", "genero", "fecha_nacimiento", "estado", "nombre_estado",
            "municipio", "nombre_municipio", "parroquia", "codigo_cv", "nombre_cv",
            "direccion_cv", "latitud", "longitud"
        ]
        writer.writerow(headers)

        # Escribir datos
        for persona in all_results:
            writer.writerow([
                persona.v_e, persona.cedula,
                persona.primer_nombre, persona.segundo_nombre,
                persona.primer_apellido, persona.segundo_apellido,
                persona.nombre_completo, persona.genero,
                persona.fecha_nacimiento.strftime("%d/%m/%Y") if persona.fecha_nacimiento else "",
                persona.estado if persona.estado is not None else "",
                persona.nombre_estado,
                persona.municipio if persona.municipio is not None else "",
                persona.nombre_municipio,
                persona.parroquia if persona.parroquia is not None else "",
                persona.codigo_cv if persona.codigo_cv is not None else "",
                persona.nombre_cv,
                persona.direccion_cv,
                persona.latitud if persona.latitud is not None else "",
                persona.longitud if persona.longitud is not None else "",
            ])

        # Preparar para la descarga
        csv_data = output.getvalue().encode("utf-8-sig")
        output.close()

        filename = f"export_resultados_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

        return rx.download(data=csv_data, filename=filename)

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
                # Limpiar cualquier separador de miles
                clean_val = re.sub(r"[^\d-]", "", val)
                return int(clean_val) if clean_val else None
            except (ValueError, TypeError):
                return None

        def to_date_or_none(val: str) -> datetime.date | None:
            """Convierte una cadena a fecha, probando formatos comunes."""
            if not val:
                return None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
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
                return float(val.replace(',', '.'))
            except (ValueError, TypeError):
                return None

        num_expected_cols = 18
        cleaned_row = [
            (row[i].strip().strip('"').strip("'") if i < len(row) and row[i] is not None else "")
            for i in range(num_expected_cols)
        ]

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

        cedula_raw = cleaned_row[CEDULA_COL]
        cedula_clean = re.sub(r"[^\d]", "", cedula_raw)
        if not cedula_clean:
            raise InvalidRowError(f"Línea {line_number}: La Cédula '{cedula_raw}' (columna {CEDULA_COL + 1}) no contiene un número válido.")
        cedula_int = int(cedula_clean)

        p_nombre = cleaned_row[PRIMER_NOMBRE_COL]
        p_apellido = cleaned_row[PRIMER_APELLIDO_COL]
        if not p_nombre or not p_apellido:
            raise InvalidRowError(f"Línea {line_number}: El primer nombre (columna {PRIMER_NOMBRE_COL + 1}) y el primer apellido (columna {PRIMER_APELLIDO_COL + 1}) son obligatorios.")

        s_nombre = cleaned_row[SEGUNDO_NOMBRE_COL]
        s_apellido = cleaned_row[SEGUNDO_APELLIDO_COL]

        partes_nombre = [p_nombre, s_nombre, p_apellido, s_apellido]
        nombre_concatenado = " ".join(p for p in partes_nombre if p)

        return {
            "v_e": (cleaned_row[V_E_COL].upper() if cleaned_row[V_E_COL] else "V"),
            "cedula": cedula_int,
            "primer_apellido": p_apellido,
            "segundo_apellido": s_apellido,
            "primer_nombre": p_nombre,
            "segundo_nombre": s_nombre,
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
        self.upload_progress = min(100, max(0, int(progress.get("progress", 0) * 100)))

    @staticmethod
    def _batch_insert(data: list[dict]):
        """Inserta un lote de datos en la base de datos en un hilo separado para no bloquear."""
        with rx.session() as session:
            session.execute(insert(Persona), data)
            session.commit()

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Procesa la subida masiva de forma ultra eficiente usando streaming y SQL Core."""
        self.cancel_upload = False
        self.upload_error_log.clear()
        self.upload_error_file_content = None
        if not files:
            self.upload_status = "Por favor, seleccione un archivo primero."
            self.upload_status_opacity = 1.0
            yield rx.toast.warning("Por favor, seleccione un archivo primero.")
            return

        for file in files:
            self.uploading = True
            self.upload_status = "Archivo en servidor. Iniciando procesamiento..."
            self.upload_status_opacity = 1.0
            self.upload_progress = 0
            yield

            line_number = 0
            delimiter = ","
            try:
                file_size = getattr(file, "size", None) or 1
                bytes_processed = 0

                first_chunk_sample = await file.read(4096)
                if not first_chunk_sample:
                    self.upload_status = "El archivo está vacío."
                    yield rx.toast.warning("El archivo está vacío.")
                    continue

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

                async def chunk_iterator_with_progress(f, file_size_bytes=file_size):
                    nonlocal bytes_processed
                    bytes_processed = 0
                    CHUNK_SIZE = 8192
                    while chunk := await f.read(CHUNK_SIZE):
                        bytes_processed += len(chunk)
                        if file_size_bytes > 1:
                            self.upload_progress = min(100, int((bytes_processed / file_size_bytes) * 100))
                        yield chunk

                async def csv_row_iterator(chunk_iter, encoding_str, delimiter_char):
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

                chunk_iter = chunk_iterator_with_progress(file, file_size)
                row_iter = csv_row_iterator(chunk_iter, encoding, delimiter)
                try:
                    first_row = await anext(row_iter)
                    line_number = 1
                except StopAsyncIteration:
                    self.upload_status = "El archivo está vacío."
                    yield rx.toast.warning("El archivo está vacío.")
                    continue

                is_header = any(char.isalpha() for char in "".join(first_row[:3]))

                registros_para_insertar = []
                total_cargados = 0

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

                async for row in row_iter:
                    line_number += 1
                    try:
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
                        continue

                    if self.cancel_upload:
                        self.upload_status = "Carga cancelada por el usuario."
                        break

                    if len(registros_para_insertar) >= self.BATCH_SIZE:
                        self.upload_status = f"Insertando lote de {len(registros_para_insertar)} registros... ({self.upload_progress}%)"
                        yield

                        await rx.run_in_thread(functools.partial(self._batch_insert, registros_para_insertar.copy()))
                        total_cargados += len(registros_para_insertar)
                        registros_para_insertar.clear()

                        self.upload_status = f"Procesando... {total_cargados} registros cargados ({self.upload_progress}%)"
                        yield

                if registros_para_insertar and not self.cancel_upload:
                    self.upload_status = f"Insertando lote final de {len(registros_para_insertar)} registros... ({self.upload_progress}%)"
                    yield
                    await rx.run_in_thread(functools.partial(self._batch_insert, registros_para_insertar.copy()))
                    total_cargados += len(registros_para_insertar)

                if not self.cancel_upload:
                    if self.upload_error_log:
                        error_buffer = io.StringIO()
                        writer = csv.writer(error_buffer)
                        writer.writerow(["line_number", "error_message", "original_row_data"])
                        for err in self.upload_error_log:
                            writer.writerow([err["line"], err["error"], err["row_data"]])
                        self.upload_error_file_content = error_buffer.getvalue()
                        error_buffer.close()

                        message = f"¡Éxito parcial! Se cargaron {total_cargados} registros. Se encontraron {len(self.upload_error_log)} errores."
                        self.upload_status = message
                        self.upload_status_opacity = 1.0
                        yield rx.toast.warning(message)
                    elif total_cargados == 0:
                        message = "No se encontraron registros válidos para cargar."
                        self.upload_status = message
                        self.upload_status_opacity = 1.0
                        yield rx.toast.warning(message)
                    else:
                        message = f"¡Éxito! Se cargaron {total_cargados} registros."
                        self.upload_status = message
                        self.upload_status_opacity = 1.0
                        self.upload_progress = 100
                        yield rx.toast.success(message)
                        await asyncio.sleep(1.2)
                        self.show_upload_dialog = False

            except (csv.Error, OSError, UnicodeDecodeError) as e:
                message = (
                    f"Error fatal en la línea ~{line_number}: {e!s}. "
                    f"Verifique que el delimitador ('{delimiter}') sea correcto y que el archivo no esté corrupto."
                )
                self.upload_status = message
                self.upload_status_opacity = 1.0
                yield rx.toast.error(message)
            except (IndexError, ValueError, TypeError, AttributeError, RuntimeError) as e:
                message = f"Error inesperado durante la carga en la línea ~{line_number}: {e!s}"
                self.upload_status = message
                self.upload_status_opacity = 1.0
                yield rx.toast.error(message)
            finally:
                self.cancel_upload = False
                self.uploading = False

    def generar_pdf_persona(self, cedula: int):
        """Genera un archivo PDF con la ficha individual de la persona consultada."""
        # Resultados es una lista de diccionarios; el PDF necesita el modelo completo.
        with rx.session() as session:
            persona = session.exec(
                sqlmodel.select(Persona).where(Persona.cedula == int(cedula))
            ).first()

        if not persona:
            return rx.toast.error("No se encontró el registro para generar la ficha PDF.")

        buffer = io.BytesIO()
        pdf_filename = f"Ficha_{persona.cedula}.pdf"

        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,
            spaceAfter=15,
        )

        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=20,
        )

        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor("#2D3748"),
        )

        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#1A202C"),
        )

        story = []

        # Encabezado
        story.append(Paragraph("SISTEMA DE CONSULTA", title_style))
        story.append(Paragraph("FICHA RESUMEN DE CONSULTA CIUDADANA", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3182CE"), spaceAfter=20))

        # --- Datos de la ficha, compartidos por el PDF y el código QR ---
        datos_ficha = [
            ("Nacionalidad (V/E)", persona.v_e or ""),
            ("Cédula de Identidad", str(persona.cedula) if persona.cedula is not None else ""),
            ("Nombres", f"{persona.primer_nombre} {persona.segundo_nombre}".strip()),
            ("Apellidos", f"{persona.primer_apellido} {persona.segundo_apellido}".strip()),
            ("Nombre Completo", persona.nombre_completo or ""),
            ("Género", persona.genero or ""),
            ("Fecha de Nacimiento", persona.fecha_nacimiento.strftime("%d/%m/%Y") if persona.fecha_nacimiento else ""),
            ("Código Estado", str(persona.estado) if persona.estado is not None else ""),
            ("Nombre Estado", persona.nombre_estado or ""),
            ("Código Municipio", str(persona.municipio) if persona.municipio is not None else ""),
            ("Nombre Municipio", persona.nombre_municipio or ""),
            ("Código Parroquia", str(persona.parroquia) if persona.parroquia is not None else ""),
            ("Código Centro Votación", str(persona.codigo_cv) if persona.codigo_cv is not None else ""),
            ("Nombre Centro Votación", persona.nombre_cv or ""),
            ("Dirección Centro Votación", persona.direccion_cv or ""),
            ("Latitud", str(persona.latitud) if persona.latitud is not None else ""),
            ("Longitud", str(persona.longitud) if persona.longitud is not None else ""),
        ]
        qr_code_data = "SISTEMA DE CONSULTA \nFICHA DE CONSULTA CIUDADANA\n\n" + "\n".join(
            f"{label}: {value}" for label, value in datos_ficha
        )
        qr_img = qrcode.make(qr_code_data, box_size=10, border=2)

        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        qr_image_for_pdf = Image(qr_buffer, width=1.5 * inch, height=1.5 * inch)
        qr_image_for_pdf.hAlign = 'CENTER'

        # --- Tabla de Datos ---
        datos = [
            [Paragraph(f"{label}:", label_style), Paragraph(value, value_style)]
            for label, value in datos_ficha
        ]

        # Tabla principal con los datos de la persona
        tabla_datos = Table(datos, colWidths=[160, 240])
        tabla_datos.setStyle(TableStyle([
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

        # --- Layout Principal (Tabla de datos a la izquierda, QR a la derecha) ---
        qr_section = [
            qr_image_for_pdf,
            Spacer(1, 6),
            Paragraph("Escanear para verificar", subtitle_style)
        ]

        main_layout_table = Table([[tabla_datos, qr_section]], colWidths=[420, 100])
        main_layout_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))

        story.append(main_layout_table)
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
                    accept={"text/plain": [".txt", ".csv"], "text/csv": [".csv"], "application/vnd.ms-excel": [".csv"]},
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
                        is_disabled=State.uploading,
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
            rx.heading(f"¡Bienvenido, {State.logged_user_username}!", size="8"),
            rx.spacer(),
            rx.cond(
                State.is_admin,
                txt_upload_dialog(),
            ),
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
                    on_key_down=State.handle_search_key_down,
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
                    on_key_down=State.handle_search_key_down,
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
                    on_key_down=State.handle_search_key_down,
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
                    on_click=State.limpiar_busqueda,
                ),
            ),
            rx.cond(
                State.logged_user_can_imprimir,
                rx.cond(
                    State.total_results > 0,
                    rx.button(
                        "Exportar a CSV",
                        icon="download",
                        color_scheme="green",
                        variant="outline",
                        on_click=State.exportar_resultados_csv,
                    ),
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
                State.logged_user_can_consultar,
                rx.fragment(
                    rx.cond(
                        State.total_results > 0,
                        rx.fragment(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        sortable_header("V/E", "v_e"),
                                        sortable_header("Cédula", "cedula"),
                                        sortable_header("Nombre Completo", "nombre_completo"),
                                        sortable_header("Fecha Nacimiento", "fecha_nacimiento"),
                                        sortable_header("Género", "genero"),
                                        sortable_header("Estado", "nombre_estado"),
                                        sortable_header("Municipio", "nombre_municipio"),
                                        sortable_header("Centro Votación", "nombre_cv"),
                                        rx.table.column_header_cell("Acción / Reporte"),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        State.resultados_display,
                                        lambda p_dict, index: rx.table.row(
                                            rx.table.cell(p_dict["v_e"]),
                                            rx.table.cell(p_dict["cedula"]),
                                            rx.table.cell(p_dict["nombre_completo"]),
                                            rx.table.cell(p_dict["fecha_nacimiento"]),
                                            rx.table.cell(p_dict["genero"]),
                                            rx.table.cell(p_dict["nombre_estado"]),
                                            rx.table.cell(p_dict["nombre_municipio"]),
                                            rx.table.cell(p_dict["nombre_cv"]),
                                            rx.table.cell(
                                                rx.cond(
                                                    State.logged_user_can_imprimir,
                                                    rx.button(
                                                        "Generar PDF",
                                                        icon="file-text",
                                                        color_scheme="red",
                                                        size="2",
                                                        variant="soft",
                                                        on_click=State.generar_pdf_persona(p_dict["cedula"]),
                                                    ),
                                                ),
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
                            rx.vstack(
                                rx.heading("Mapa de los resultados", size="5"),
                                rx.text("Los marcadores corresponden a los 10 registros de esta página.", size="2", color_scheme="gray"),
                                rx.el.iframe(
                                    src=State.search_map_url,
                                    width="100%",
                                    height="480px",
                                    border="0",
                                    border_radius="8px",
                                ),
                                width="100%",
                                spacing="2",
                                padding_top="1rem",
                            ),
                        ),
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
                            ),
                        ),
                    ),
                ),
                rx.center(
                    rx.callout("No tiene permisos para realizar consultas.", icon="lock", color_scheme="red", margin_y="2rem"),
                    width="100%",
                ),
            ),
        ),
        width="100%",
        spacing="5",
        padding_y="2rem",
    )

def municipality_view() -> rx.Component:
    municipality_options = [
        "MP. ARISMENDI",
        "MP. DIAZ",
        "MP. GOMEZ",
        "MP. MANEIRO",
        "MP. MARCANO",
        "MP. MARIÑO",
        "MP.PENIN. DE MACANAO",
        "MP.VILLALBA(I.COCHE)",
        "MP. TUBORES",
        "MP.ANTOLIN DEL CAMPO",
        "MP. GARCIA",
    ]

    def municipality_filter_row(filter_data: dict, index: int) -> rx.Component:
        return rx.grid(
            rx.select(
                municipality_options,
                placeholder="Seleccione un municipio",
                value=filter_data["municipio"],
                on_change=lambda value: State.set_municipality_filter(index, "municipio", value),
                size="3",
                width="100%",
            ),
            rx.vstack(
                rx.text("Centros de votación", weight="bold", size="2"),
                rx.cond(
                    State.municipality_cv_options[index],
                    rx.vstack(
                        rx.foreach(
                            State.municipality_cv_options[index],
                            lambda center: rx.checkbox(
                                center,
                                checked=State.municipality_selected_cvs[index].contains(center),
                                on_change=lambda checked: State.toggle_municipality_cv(index, center, checked),
                            ),
                        ),
                        max_height="180px",
                        overflow_y="auto",
                        align="start",
                        spacing="2",
                    ),
                    rx.text("Seleccione primero un municipio", size="2", color_scheme="gray"),
                ),
                width="100%",
            ),
            rx.cond(
                index > 0,
                rx.button(
                    rx.icon("trash-2"),
                    variant="soft",
                    color_scheme="red",
                    on_click=lambda: State.remove_municipality_filter(index),
                    aria_label="Eliminar filtro",
                ),
            ),
            width="100%",
            spacing="3",
            align="center",
            columns={"initial": "1", "md": "minmax(220px, 1fr) minmax(280px, 2fr) auto"},
        )

    return rx.vstack(
        rx.heading("Consulta por Municipio", size="8"),
        rx.text("Filtra por municipio y, opcionalmente, por centro de votación.", color_scheme="gray"),
        rx.input(
            value=State.municipality_state,
            is_disabled=True,
            size="3",
            width="100%",
        ),
        rx.vstack(
            rx.foreach(State.municipality_filters, municipality_filter_row),
            rx.hstack(
                rx.button(
                    "Buscar otro",
                    icon="plus",
                    variant="soft",
                    on_click=State.add_municipality_filter,
                ),
                rx.button(
                    "Consultar mapa",
                    icon="map",
                    size="3",
                    color_scheme="blue",
                    on_click=State.buscar_municipio,
                ),
                rx.cond(
                    State.has_municipality_filters,
                    rx.button("Limpiar", icon="x", variant="soft", on_click=State.limpiar_municipio),
                ),
                spacing="3",
            ),
            width="100%",
            spacing="3",
        ),
        rx.cond(
            State.municipality_is_loading,
            rx.vstack(rx.progress(width="100%"), rx.text("Buscando centros de votación...", color_scheme="gray"), width="100%", padding_y="3rem"),
            rx.cond(
                State.municipality_total > 0,
                rx.vstack(
                    rx.text(f"{State.municipality_total} ciudadanos encontrados", weight="bold"),
                    rx.heading("Mapa de resultados", size="5"),
                    rx.el.iframe(
                        src=State.municipality_map_url,
                        width="100%",
                        height="540px",
                        border="0",
                        border_radius="8px",
                    ),
                    rx.cond(
                        State.municipality_detail_prompt,
                        rx.vstack(
                            rx.text("¿Desea mostrar la tabla con el detalle completo?", weight="bold"),
                            rx.hstack(
                                rx.button(
                                    "Sí, mostrar detalle",
                                    icon="table-2",
                                    color_scheme="blue",
                                    on_click=State.buscar_detalle_municipio,
                                ),
                                rx.button(
                                    "No, nueva búsqueda",
                                    icon="x",
                                    variant="soft",
                                    on_click=State.rechazar_detalle_municipio,
                                ),
                                spacing="3",
                            ),
                            spacing="3",
                            padding_top="1rem",
                        ),
                    ),
                    rx.cond(
                        State.municipality_detail_is_loading,
                        rx.vstack(
                            rx.progress(width="100%"),
                            rx.text("Cargando detalle completo...", color_scheme="gray"),
                            width="100%",
                            padding_y="2rem",
                        ),
                    ),
                    rx.cond(
                        State.municipality_detail_total > 0,
                        rx.fragment(
                            rx.heading("Tabla de detalle completo", size="5", padding_top="1rem"),
                            rx.hstack(
                                rx.text(f"Página {State.municipality_detail_page} de {State.municipality_detail_total_pages} ({State.municipality_detail_total} registros)"),
                                rx.spacer(),
                                rx.text("Registros por página:"),
                                rx.select(
                                    ["10", "25", "50", "100", "all"],
                                    value=State.municipality_detail_page_size_label,
                                    on_change=State.set_municipality_detail_page_size,
                                    size="2",
                                ),
                                rx.cond(
                                    State.logged_user_can_imprimir,
                                    rx.button(
                                        "Descargar CSV completo",
                                        icon="download",
                                        color_scheme="green",
                                        variant="soft",
                                        on_click=State.exportar_detalle_municipio_csv,
                                        size="2",
                                    ),
                                ),
                                rx.button(
                                    "Anterior",
                                    on_click=State.previous_municipality_detail_page,
                                    is_disabled=State.municipality_detail_page <= 1,
                                    size="2",
                                ),
                                rx.button(
                                    "Siguiente",
                                    on_click=State.next_municipality_detail_page,
                                    is_disabled=State.municipality_detail_page >= State.municipality_detail_total_pages,
                                    size="2",
                                ),
                                width="100%",
                                wrap="wrap",
                                align="center",
                                spacing="3",
                            ),
                            rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("V/E"),
                                    rx.table.column_header_cell("Cédula"),
                                    rx.table.column_header_cell("Nombre Completo"),
                                    rx.table.column_header_cell("Primer Nombre"),
                                    rx.table.column_header_cell("Segundo Nombre"),
                                    rx.table.column_header_cell("Primer Apellido"),
                                    rx.table.column_header_cell("Segundo Apellido"),
                                    rx.table.column_header_cell("Fecha Nacimiento"),
                                    rx.table.column_header_cell("Género"),
                                    rx.table.column_header_cell("Código Estado"),
                                    rx.table.column_header_cell("Estado"),
                                    rx.table.column_header_cell("Código Municipio"),
                                    rx.table.column_header_cell("Municipio"),
                                    rx.table.column_header_cell("Parroquia"),
                                    rx.table.column_header_cell("Código CV"),
                                    rx.table.column_header_cell("Centro Votación"),
                                    rx.table.column_header_cell("Dirección"),
                                    rx.table.column_header_cell("Latitud"),
                                    rx.table.column_header_cell("Longitud"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    State.municipality_detail_display,
                                    lambda p: rx.table.row(
                                        rx.table.cell(p["v_e"]), rx.table.cell(p["cedula"]),
                                        rx.table.cell(p["nombre_completo"]), rx.table.cell(p["primer_nombre"]),
                                        rx.table.cell(p["segundo_nombre"]), rx.table.cell(p["primer_apellido"]),
                                        rx.table.cell(p["segundo_apellido"]), rx.table.cell(p["fecha_nacimiento"]),
                                        rx.table.cell(p["genero"]), rx.table.cell(p["estado"]),
                                        rx.table.cell(p["nombre_estado"]), rx.table.cell(p["municipio"]),
                                        rx.table.cell(p["nombre_municipio"]), rx.table.cell(p["parroquia"]),
                                        rx.table.cell(p["codigo_cv"]), rx.table.cell(p["nombre_cv"]),
                                        rx.table.cell(p["direccion_cv"]), rx.table.cell(p["latitud"]),
                                        rx.table.cell(p["longitud"]),
                                    ),
                                ),
                            ),
                            width="max-content",
                        ),
                        width="100%",
                        overflow_x="auto",
                            ),
                        ),
                    ),
                    width="100%",
                    spacing="3",
                ),
                rx.cond(
                    State.has_municipality_filters,
                    rx.callout("No se encontraron ciudadanos para los filtros seleccionados.", icon="info", color_scheme="blue"),
                ),
            ),
        ),
        width="100%",
        spacing="4",
        padding_y="2rem",
    )

    return rx.vstack(
        rx.heading("Consulta por Municipio", size="8"),
        rx.text("Consulta todos los ciudadanos asociados al municipio y ubícalos en el mapa.", color_scheme="gray"),
        rx.grid(
            rx.input(
                value=State.municipality_state,
                is_disabled=True,
                size="3",
                width="100%",
            ),
            rx.select(
                [
                    "MP. ARISMENDI",
                    "MP. DIAZ",
                    "MP. GOMEZ",
                    "MP. MANEIRO",
                    "MP. MARCANO",
                    "MP. MARIÑO",
                    "MP.PENIN. DE MACANAO",
                    "MP.VILLALBA(I.COCHE)",
                    "MP. TUBORES",
                    "MP.ANTOLIN DEL CAMPO",
                    "MP. GARCIA",
                ],
                placeholder="Seleccione un municipio",
                value="",
                size="3",
                width="100%",
            ),
            rx.button("Buscar Municipio", icon="map", size="3", color_scheme="blue", on_click=State.buscar_municipio),
            rx.cond(
                State.has_municipality_filters,
                rx.button("Limpiar", icon="x", variant="soft", on_click=State.limpiar_municipio),
            ),
            columns={"initial": "1", "sm": "3"},
            spacing="3",
        ),
        rx.cond(
            State.municipality_is_loading,
            rx.vstack(rx.progress(width="100%"), rx.text("Buscando ciudadanos...", color_scheme="gray"), width="100%", padding_y="3rem"),
            rx.cond(
                State.municipality_total > 0,
                rx.vstack(
                    rx.text(f"{State.municipality_total} ciudadanos encontrados", weight="bold"),
                    rx.heading("Mapa de resultados", size="5"),
                    rx.el.iframe(
                        src=State.municipality_map_url,
                        width="100%",
                        height="540px",
                        border="0",
                        border_radius="8px",
                    ),
                    rx.heading("Listado completo", size="5", padding_top="1rem"),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("V/E"),
                                    rx.table.column_header_cell("Cédula"),
                                    rx.table.column_header_cell("Nombre Completo"),
                                    rx.table.column_header_cell("Primer Nombre"),
                                    rx.table.column_header_cell("Segundo Nombre"),
                                    rx.table.column_header_cell("Primer Apellido"),
                                    rx.table.column_header_cell("Segundo Apellido"),
                                    rx.table.column_header_cell("Fecha Nacimiento"),
                                    rx.table.column_header_cell("Género"),
                                    rx.table.column_header_cell("Código Estado"),
                                    rx.table.column_header_cell("Estado"),
                                    rx.table.column_header_cell("Código Municipio"),
                                    rx.table.column_header_cell("Municipio"),
                                    rx.table.column_header_cell("Parroquia"),
                                    rx.table.column_header_cell("Código CV"),
                                    rx.table.column_header_cell("Centro Votación"),
                                    rx.table.column_header_cell("Dirección"),
                                    rx.table.column_header_cell("Latitud"),
                                    rx.table.column_header_cell("Longitud"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    State.municipality_results,
                                    lambda p: rx.table.row(
                                        rx.table.cell(p["v_e"]),
                                        rx.table.cell(p["cedula"]),
                                        rx.table.cell(p["nombre_completo"]),
                                        rx.table.cell(p["primer_nombre"]),
                                        rx.table.cell(p["segundo_nombre"]),
                                        rx.table.cell(p["primer_apellido"]),
                                        rx.table.cell(p["segundo_apellido"]),
                                        rx.table.cell(p["fecha_nacimiento"]),
                                        rx.table.cell(p["genero"]),
                                        rx.table.cell(p["estado"]),
                                        rx.table.cell(p["nombre_estado"]),
                                        rx.table.cell(p["municipio"]),
                                        rx.table.cell(p["nombre_municipio"]),
                                        rx.table.cell(p["parroquia"]),
                                        rx.table.cell(p["codigo_cv"]),
                                        rx.table.cell(p["nombre_cv"]),
                                        rx.table.cell(p["direccion_cv"]),
                                        rx.table.cell(p["latitud"]),
                                        rx.table.cell(p["longitud"]),
                                    ),
                                ),
                            ),
                            width="max-content",
                        ),
                        width="100%",
                        overflow_x="auto",
                    ),
                    width="100%",
                    spacing="3",
                ),
                rx.cond(
                    State.has_municipality_filters,
                    rx.callout("No se encontraron ciudadanos para ese municipio.", icon="info", color_scheme="blue"),
                ),
            ),
        ),
        width="100%",
        spacing="4",
        padding_y="2rem",
    )

def delete_user_dialog() -> rx.Component:
    """Diálogo de confirmación para eliminar un usuario."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Confirmar Eliminación"),
            rx.alert_dialog.description(
                "¿Estás seguro de que quieres eliminar al usuario '",
                rx.text(State.deleting_user_username, as_="span", weight="bold"),
                "'? Esta acción no se puede deshacer.",
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
            rx.vstack(
                rx.dialog.title(f"Editando Usuario: {State.edit_user_username}"),
                rx.dialog.description("Modifica los detalles del usuario y guarda los cambios."),
                rx.flex(
                    rx.text("Rol:", weight="bold"),
                    rx.select(
                        ["admin", "usuario"],
                        value=State.edit_user_rol,
                        on_change=State.set_edit_user_rol,
                    ),
                    direction="column",
                    spacing="2",
                ),
                rx.flex(
                    rx.text("Estado:", weight="bold"),
                    rx.hstack(
                        rx.text("Inactivo"),
                        rx.switch(
                            checked=State.edit_user_activo,
                            on_change=State.set_edit_user_activo,
                        ),
                        rx.text("Activo"),
                        spacing="2",
                        align="center",
                    ),
                    direction="column",
                    spacing="2",
                ),
                rx.flex(
                    rx.text("Permisos:", weight="bold"),
                    rx.hstack(
                        rx.text("Consultar"),
                        rx.switch(
                            checked=State.edit_user_can_consultar,
                            on_change=State.set_edit_user_can_consultar,
                        ),
                        rx.spacer(),
                        rx.text("Imprimir/Exportar"),
                        rx.switch(
                            checked=State.edit_user_can_imprimir,
                            on_change=State.set_edit_user_can_imprimir,
                        ),
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
                        value=State.edit_password_input,
                        on_change=State.set_edit_password_input,
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
                    rx.text("Permisos", margin_top="1rem"),
                    rx.hstack(
                        rx.text("Consultar"),
                        rx.switch(
                            checked=State.new_user_can_consultar,
                            on_change=State.set_new_user_can_consultar,
                        ),
                        rx.spacer(),
                        rx.text("Imprimir/Exportar"),
                        rx.switch(
                            checked=State.new_user_can_imprimir,
                            on_change=State.set_new_user_can_imprimir,
                        ),
                        spacing="2",
                        align="center",
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
                            icon=rx.cond(State.form_message_color == "red", "triangle-alert", "check-circle"),
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
                                            on_click=State.start_edit_user(user),
                                            size="2",
                                        ),
                                        rx.button(
                                            "Eliminar",
                                            icon="trash-2",
                                            color_scheme="red",
                                            on_click=State.start_delete_user(user),
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
                    rx.drawer.close(
                        rx.button(
                            rx.hstack(rx.icon("map"), rx.text("Consulta por Municipio")),
                            on_click=lambda: State.set_dashboard_view("municipality"),
                            variant="ghost",
                            width="100%",
                            justify_content="flex-start",
                        ),
                        as_child=True,
                    ),
                    rx.cond(
                        State.is_admin,
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
                    rx.icon("user", color="white"),
                    rx.text(State.logged_user_username, color="white"),
                    variant="soft",
                    color_scheme="gray",
                )
            ),
            rx.menu.content(
                rx.cond(
                    State.is_admin,
                    rx.fragment(
                        rx.menu.item("Perfil", icon="user-check", on_click=rx.toast.info("Función de perfil no implementada.")),
                        rx.menu.item("Ajustes", icon="settings", on_click=lambda: State.set_dashboard_view("admin_users")),
                        rx.menu.separator(),
                    ),
                ),
                rx.menu.item("Consulta por Municipio", icon="map", on_click=lambda: State.set_dashboard_view("municipality")),
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
        position="fixed",
        top="0",
        z_index="100",
        background_color="#1A365D",
    )

def login_view() -> rx.Component:
    """Vista de inicio de sesión con diseño moderno de dos columnas."""
    return rx.grid(
        rx.box(
            rx.vstack(
                rx.heading("Sistema de Consultas", size="8", weight="bold", text_align="center"),
                rx.text("Inicia sesión para acceder al Sistema", color_scheme="gray", text_align="center"),
                rx.box(height="16px"),
                rx.cond(
                    State.error_msg != "",
                    rx.callout(State.error_msg, icon="triangle-alert", color_scheme="red", role="alert", width="100%"),
                ),
                rx.text("Nombre de Usuario", weight="medium", margin_bottom="-10px"),
                rx.input(
                    rx.icon("user"),
                    placeholder="tu_usuario",
                    value=State.input_user,
                    on_change=State.set_input_user,
                    on_key_down=State.handle_login_key_down,
                    size="3",
                    width="100%",
                ),
                rx.text("Contraseña", weight="medium", margin_bottom="-10px"),
                rx.input(
                    rx.icon("lock"),
                    type="password",
                    placeholder="••••••••",
                    value=State.input_pass,
                    on_change=State.set_input_pass,
                    on_key_down=State.handle_login_key_down,
                    size="3",
                    width="100%",
                ),
                rx.box(height="8px"),
                rx.button("Ingresar", icon="arrow-right", width="100%", size="3", color_scheme="blue", on_click=State.login),
                spacing="4",
                width="350px",
                align="center",
            ),
            width="100%",
            height="100%",
            display="flex",
            justify_content="center",
            align_items="center",
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="10",
        ),
        rx.box(
            background_image="url(/login_bg.jpg)",
            background_size="cover",
            background_position="center",
            height="100%",
            display=["none", "none", "block"],
        ),
        columns="2",
        height="100vh",
        width="100%",
        gap="0",
        template_columns=["1fr", "1fr"],
    )

def main_dashboard() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.cond(
                State.current_dashboard_view == "search",
                search_view(),
                rx.cond(
                    State.current_dashboard_view == "municipality",
                    municipality_view(),
                    admin_view(),
                ),
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
        rx.cond(State.is_logged_in, main_dashboard(), login_view()),
        rx.toast.provider(),
    )


app = rx.App()
app.add_page(
    index,
    title="Sistema de Consultas",
    on_load=State.crear_usuario_inicial,
)