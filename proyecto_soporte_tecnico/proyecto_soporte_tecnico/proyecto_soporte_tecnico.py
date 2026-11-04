"""¡Bienvenido a mi proyecto_soporte_tecnico! Este archivo es un monolito con toda la estructura de la aplicación que evolucionará a una estructura distribuida o modular para lograr una Arquitectura de Microservicios: por Leobaldo Meza."""
from datetime import datetime, timezone
from typing import Any

import reflex as rx

# ==========================================
# 1. CONSTANTES Y CONFIGURACIÓN
# ==========================================

DIRECCIONES = [
    "1X10 DEL BUEN GOB.",
    "DIRECCION DE CIENCIA, TECNOLOGIA E INNOVACION",
    "DIRECCION DE INFRAESTRUCTURA",
    "DIRECCION DE LA SECRETARIA DEL DESPACHO",
    "DIRECCION DE SALUD",
    "DIRECCION EJECUTIVA DE GESTION URBANA",
    "DIRECCION EJECUTIVA DE PARTICIPACION Y PODER POPULAR",
    "FUNDACION SOCIAL SANTIAGO MARIÑO",
    "INSTITUTO AUTONOMO MUNICIPAL DE DEPORTE, JUVENTUD Y RECREACION",
    "INSTITUTO AUTONOMO SOCIALISTA DE VIVIENDA Y HABITAD DEL MUNICIPIO",
    "INSTITUTO MUNICIPAL DE PROTECCIÓN CIVIL Y ADMINISTRACION DE DESASTRES",
    "JEFA DE RECEPCIÓN",
    "RECEPCION 1X10 DEL BUEN GOB.",
    "RECEPCION FUNDACION SOCIAL SANTIAGO MARIÑO",
    "TALENTO HUMANO",
]

# ==========================================
# 2. ESTADO GLOBAL DE LA APLICACIÓN (STATE)
# ==========================================

class State(rx.State):
    # --- Sesión de Usuario ---
    logged_in: bool = False
    usuario_actual: str = ""
    direccion_actual: str = ""
    es_admin: bool = False
    
    # --- Control de UI / Panel Lateral Colapsable ---
    sidebar_colapsado: bool = False
    pestana_chat_activa: str = "historial"  # "historial" o "nuevo"

    # --- Formulario de Login ---
    login_user: str = ""
    login_pass: str = ""
    login_error: str = ""

    # --- Formulario de Registro ---
    reg_nombre: str = ""
    reg_user: str = ""
    reg_pass: str = ""
    reg_direccion: str = DIRECCIONES[1]
    reg_error: str = ""
    reg_exito: str = ""

    # --- Formulario de Recuperación ---
    reset_user: str = ""
    reset_pass: str = ""
    reset_msg: str = ""

    # --- Formulario de Inventario ---
    inv_codigo: str = ""
    inv_nombre: str = ""
    inv_categoria: str = "Periféricos"
    inv_cantidad: int = 1
    inv_estado: str = "Nuevo"

    # --- Ticket Seleccionado para Detalle/Impresión/Edición ---
    ticket_seleccionado: dict[str, Any] = rx.field(default_factory=dict)
    modal_impresion_abierto: bool = False
    nota_tecnica_temp: str = ""

    # --- Lista de Usuarios Registrados ---
    usuarios_registrados: list[dict[str, Any]] = rx.field(
        default_factory=lambda: [
            {
                "user": "admin",
                "pass": "admin123",
                "nombre": "Administrador General",
                "direccion": "DIRECCION DE CIENCIA, TECNOLOGIA E INNOVACION",
                "es_admin": True
            },
            {
                "user": "solicitante",
                "pass": "123456",
                "nombre": "Usuario Solicitante",
                "direccion": "TALENTO HUMANO",
                "es_admin": False
            }
        ]
    )

    # --- Inventario Local ---
    inventario: list[dict[str, Any]] = rx.field(
        default_factory=lambda: [
            {"codigo": "COMP-001", "nombre": "Disco Duro SSD 500GB", "categoria": "Almacenamiento", "cantidad": 12, "estado": "Nuevo"},
            {"codigo": "COMP-002", "nombre": "Memoria RAM DDR4 8GB", "categoria": "Memorias", "cantidad": 8, "estado": "Nuevo"},
            {"codigo": "COMP-003", "nombre": "Teclado USB Estándar", "categoria": "Periféricos", "cantidad": 5, "estado": "Usado - Buen Estado"},
        ]
    )

    # --- Navegación ---
    menu_activo: str = "chat"  # "chat" por defecto para enfocar la vista del usuario
    
    # --- Filtros y Paginación ---
    busqueda: str = ""
    filtro_estado: str = "Todos"
    filtro_direccion: str = "Todas"
    pagina_actual: int = 1
    items_por_pagina: int = 10
    
    # --- Chat de Soporte ---
    nuevo_mensaje_chat: str = ""
    asunto_chat_temp: str = ""
    historial_chat: list[dict[str, Any]] = rx.field(
        default_factory=lambda: [
            {
                "id": 1,
                "emisor": "Sistema de Soporte",
                "mensaje": "¡Hola! Bienvenido al sistema de autogestión de soporte técnico. ¿En qué podemos ayudarte hoy?",
                "fecha": "09:00 AM",
                "es_soporte": True,
            }
        ]
    )

    # --- Lista de Tickets ---
    tickets: list[dict[str, Any]] = rx.field(default_factory=list)

    # --- Métodos de UI ---
    def toggle_sidebar(self):
        self.sidebar_colapsado = not self.sidebar_colapsado

    def set_pestana_chat(self, pestana: str):
        self.pestana_chat_activa = pestana

    # --- Autenticación ---
    def set_login_user(self, val: str): self.login_user = val; self.login_error = ""
    def set_login_pass(self, val: str): self.login_pass = val; self.login_error = ""
    def set_reg_nombre(self, val: str): self.reg_nombre = val
    def set_reg_user(self, val: str): self.reg_user = val
    def set_reg_pass(self, val: str): self.reg_pass = val
    def set_reg_direccion(self, val: str): self.reg_direccion = val
    def set_reset_user(self, val: str): self.reset_user = val
    def set_reset_pass(self, val: str): self.reset_pass = val
    def set_nota_tecnica_temp(self, val: str): self.nota_tecnica_temp = val
    def set_asunto_chat_temp(self, val: str): self.asunto_chat_temp = val

    def iniciar_sesion(self):
        user_input = self.login_user.strip().lower()
        pass_input = self.login_pass.strip()

        for u in self.usuarios_registrados:
            if u["user"].lower() == user_input and u["pass"] == pass_input:
                self.logged_in = True
                self.usuario_actual = u["nombre"]
                self.direccion_actual = u["direccion"]
                self.es_admin = u["es_admin"]
                self.login_error = ""
                self.login_user = ""
                self.login_pass = ""
                self.cargar_datos_ejemplo()
                return rx.window_alert("🔔 Notificación: Bienvenido al Sistema de Soporte Técnico")

        self.login_error = "Usuario o contraseña incorrectos"

    def registrar_usuario(self):
        if not self.reg_nombre.strip() or not self.reg_user.strip() or not self.reg_pass.strip():
            self.reg_error = "Todos los campos son obligatorios"
            self.reg_exito = ""
            return

        user_input = self.reg_user.strip().lower()
        for u in self.usuarios_registrados:
            if u["user"].lower() == user_input:
                self.reg_error = "El nombre de usuario ya existe"
                self.reg_exito = ""
                return

        nuevo_u = {
            "user": user_input,
            "pass": self.reg_pass.strip(),
            "nombre": self.reg_nombre.strip(),
            "direccion": self.reg_direccion,
            "es_admin": False
        }
        self.usuarios_registrados.append(nuevo_u)
        self.reg_exito = "¡Usuario registrado con éxito! Ya puedes iniciar sesión."
        self.reg_error = ""
        self.reg_nombre = ""
        self.reg_user = ""
        self.reg_pass = ""

    def recuperar_contrasena(self):
        if not self.reset_user.strip() or not self.reset_pass.strip():
            self.reset_msg = "Ingresa usuario y nueva contraseña."
            return

        user_input = self.reset_user.strip().lower()
        for u in self.usuarios_registrados:
            if u["user"].lower() == user_input:
                u["pass"] = self.reset_pass.strip()
                self.reset_msg = "Contraseña actualizada con éxito."
                self.reset_user = ""
                self.reset_pass = ""
                return

        self.reset_msg = "El usuario no se encuentra registrado."

    def cerrar_sesion(self):
        self.logged_in = False
        self.usuario_actual = ""
        self.direccion_actual = ""
        self.es_admin = False
        self.menu_activo = "chat"

    # --- Acciones Admin ---
    def cambiar_rol_usuario(self, username: str):
        for u in self.usuarios_registrados:
            if u["user"] == username:
                u["es_admin"] = not u["es_admin"]
                break

    def cambiar_estado_ticket(self, ticket_id: int, nuevo_estado: str):
        for t in self.tickets:
            if t["id"] == ticket_id:
                t["estado"] = nuevo_estado
                return rx.window_alert(f"📱 Notificación Móvil: El ticket #{ticket_id} cambió su estatus a '{nuevo_estado}'")

    def guardar_nota_tecnica(self):
        if not self.ticket_seleccionado:
            return
        t_id = self.ticket_seleccionado.get("id")
        for t in self.tickets:
            if t["id"] == t_id:
                t["nota_tecnica"] = self.nota_tecnica_temp
                self.ticket_seleccionado["nota_tecnica"] = self.nota_tecnica_temp
                return rx.window_alert("Observación guardada y notificada al usuario.")

    # --- Modal Impresión/Detalle ---
    def ver_detalle_ticket(self, ticket: dict[str, Any]):
        self.ticket_seleccionado = ticket
        self.nota_tecnica_temp = ticket.get("nota_tecnica", "")
        self.modal_impresion_abierto = True

    def cerrar_modal_impresion(self):
        self.modal_impresion_abierto = False

    # --- Inventario ---
    def set_inv_codigo(self, val: str): self.inv_codigo = val
    def set_inv_nombre(self, val: str): self.inv_nombre = val
    def set_inv_categoria(self, val: str): self.inv_categoria = val
    def set_inv_cantidad(self, val: str):
        try:
            self.inv_cantidad = int(val) if val.strip() != "" else 0
        except ValueError:
            self.inv_cantidad = 0
    def set_inv_estado(self, val: str): self.inv_estado = val

    def agregar_item_inventario(self):
        if not self.inv_codigo.strip() or not self.inv_nombre.strip():
            return
        nuevo_item = {
            "codigo": self.inv_codigo.strip().upper(),
            "nombre": self.inv_nombre.strip(),
            "categoria": self.inv_categoria,
            "cantidad": int(self.inv_cantidad),
            "estado": self.inv_estado
        }
        self.inventario.append(nuevo_item)
        self.inv_codigo = ""
        self.inv_nombre = ""
        self.inv_cantidad = 1

    # --- Búsqueda y Paginación ---
    def set_busqueda(self, busqueda: str):
        self.busqueda = busqueda
        self.pagina_actual = 1

    def set_filtro_direccion(self, direccion: str):
        self.filtro_direccion = direccion
        self.pagina_actual = 1

    def set_nuevo_mensaje_chat(self, mensaje: str):
        self.nuevo_mensaje_chat = mensaje

    def cargar_datos_ejemplo(self):
        if not self.tickets:
            ejemplos = []
            estados = ["En Proceso", "En Progreso", "Hecho"]
            prioridades = ["Alta", "Media", "Baja"]
            
            for i in range(1, 15):
                dir_index = (i - 1) % len(DIRECCIONES)
                est_index = (i - 1) % len(estados)
                prio_index = (i - 1) % len(prioridades)
                
                ejemplos.append({
                    "id": i,
                    "usuario_nombre": f"Usuario Demo {i}",
                    "direccion": DIRECCIONES[dir_index],
                    "asunto": f"Solicitud de soporte técnico #{i}",
                    "mensaje": f"Requiero asistencia técnica en la oficina #{i}.",
                    "estado": estados[est_index],
                    "prioridad": prioridades[prio_index],
                    "fecha": f"2026-07-{(i%20)+1:02d} 09:30",
                    "nota_tecnica": "Atendido sin inconvenientes." if estados[est_index] == "Hecho" else ""
                })
            self.tickets = ejemplos

    # --- Chat Avanzado con Notificación ---
    def enviar_mensaje_chat(self):
        if not self.nuevo_mensaje_chat.strip():
            return
        
        # Generar hora y fecha usando la zona horaria UTC explícita
        ahora = datetime.now(tz=timezone.utc)
        hora_actual = ahora.strftime("%I:%M %p")
        asunto = self.asunto_chat_temp.strip() if self.asunto_chat_temp.strip() else "Consulta por Chat"
        
        nuevo_msg = {
            "id": len(self.historial_chat) + 1,
            "emisor": self.usuario_actual,
            "mensaje": self.nuevo_mensaje_chat,
            "fecha": hora_actual,
            "es_soporte": False,
        }
        self.historial_chat.append(nuevo_msg)

        # Se registra/actualiza el ticket automático
        nuevo_ticket = {
            "id": len(self.tickets) + 1,
            "usuario_nombre": self.usuario_actual,
            "direccion": self.direccion_actual,
            "asunto": asunto,
            "mensaje": self.nuevo_mensaje_chat,
            "estado": "En Proceso",
            "prioridad": "Media",
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nota_tecnica": ""
        }
        self.tickets.insert(0, nuevo_ticket)
        self.nuevo_mensaje_chat = ""
        self.asunto_chat_temp = ""
        self.pestana_chat_activa = "historial"

        return rx.window_alert("📱 ¡Notificación Enviada! Su solicitud ha sido enviada al equipo de Soporte Técnico.")

    def manejar_tecla_chat(self, key: str):
        if key == "Enter":
            return self.enviar_mensaje_chat()

    # --- Computados / Getters ---
    @rx.var
    def ultima_solicitud_usuario(self) -> dict[str, Any]:
        user_tickets = [t for t in self.tickets if t["usuario_nombre"] == self.usuario_actual]
        if user_tickets:
            return user_tickets[0]
        return {
            "id": "N/A",
            "asunto": "Sin solicitudes activas",
            "estado": "Sin Registros",
            "fecha": "-",
            "mensaje": "Aún no has registrado solicitudes de soporte."
        }

    @rx.var
    def tasa_solucion(self) -> str:
        total = self.total_tickets
        if total == 0:
            return "0.0%"
        porcentaje = (self.total_hechos / total) * 100
        return f"{porcentaje:.1f}%"

    @rx.var
    def total_tickets(self) -> int: return len(self.tickets)

    @rx.var
    def total_en_proceso(self) -> int:
        return len([t for t in self.tickets if t["estado"] == "En Proceso"])

    @rx.var
    def total_en_progreso(self) -> int:
        return len([t for t in self.tickets if t["estado"] == "En Progreso"])

    @rx.var
    def total_hechos(self) -> int:
        return len([t for t in self.tickets if t["estado"] == "Hecho"])

    @rx.var
    def datos_grafico_estados(self) -> list[dict[str, Any]]:
        return [
            {"estado": "En Proceso", "cantidad": self.total_en_proceso},
            {"estado": "En Progreso", "cantidad": self.total_en_progreso},
            {"estado": "Completados", "cantidad": self.total_hechos},
        ]

    @rx.var
    def tickets_filtrados(self) -> list[dict[str, Any]]:
        resultado = self.tickets

        if self.filtro_estado != "Todos":
            if self.filtro_estado == "Mis Tickets":
                resultado = [t for t in resultado if t["usuario_nombre"] == self.usuario_actual]
            else:
                resultado = [t for t in resultado if t["estado"] == self.filtro_estado]

        if self.filtro_direccion != "Todas":
            resultado = [t for t in resultado if t["direccion"] == self.filtro_direccion]

        if self.busqueda.strip():
            query = self.busqueda.lower()
            resultado = [
                t for t in resultado 
                if query in t["usuario_nombre"].lower() or query in t["mensaje"].lower() or query in t["asunto"].lower()
            ]

        return resultado

    @rx.var
    def tickets_paginados(self) -> list[dict[str, Any]]:
        inicio = (self.pagina_actual - 1) * self.items_por_pagina
        fin = inicio + self.items_por_pagina
        return self.tickets_filtrados[inicio:fin]

    @rx.var
    def total_paginas(self) -> int:
        total = len(self.tickets_filtrados)
        return max(1, (total + self.items_por_pagina - 1) // self.items_por_pagina)

    # --- Acciones Generales ---
    def cambiar_filtro(self, nuevo_filtro: str):
        self.filtro_estado = nuevo_filtro
        self.pagina_actual = 1

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas:
            self.pagina_actual += 1

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1

    def set_menu(self, menu: str):
        self.menu_activo = menu

# ==========================================
# 3. COMPONENTES Y VISTAS UI
# ==========================================

def panel_lateral_sidebar() -> rx.Component:
    """Panel de navegación lateral colapsable / recogible."""
    return rx.vstack(
        rx.hstack(
            rx.icon("headset", size=24, color="var(--accent-9)"),
            rx.cond(
                ~State.sidebar_colapsado,
                rx.text("Soporte Técnico", weight="bold", size="3"),
            ),
            rx.spacer(),
            rx.button(
                rx.icon(rx.cond(State.sidebar_colapsado, "panel-left-open", "panel-left-close"), size=18),
                variant="ghost",
                on_click=State.toggle_sidebar,
            ),
            width="100%", align="center", padding_bottom="1em"
        ),
        rx.divider(),
        rx.vstack(
            rx.button(
                rx.icon("message-square", size=20),
                rx.cond(~State.sidebar_colapsado, rx.text("Chat / Solicitud")),
                variant=rx.cond(State.menu_activo == "chat", "solid", "ghost"),
                on_click=lambda: State.set_menu("chat"),
                width="100%", justify="start",
            ),
            rx.button(
                rx.icon("layout-dashboard", size=20),
                rx.cond(~State.sidebar_colapsado, rx.text("Dashboard")),
                variant=rx.cond(State.menu_activo == "dashboard", "solid", "ghost"),
                on_click=lambda: State.set_menu("dashboard"),
                width="100%", justify="start",
            ),
            rx.cond(
                State.es_admin,
                rx.vstack(
                    rx.button(
                        rx.icon("bar-chart-3", size=20),
                        rx.cond(~State.sidebar_colapsado, rx.text("Reportes")),
                        variant=rx.cond(State.menu_activo == "reportes", "solid", "ghost"),
                        on_click=lambda: State.set_menu("reportes"),
                        width="100%", justify="start",
                    ),
                    rx.button(
                        rx.icon("shield-check", size=20),
                        rx.cond(~State.sidebar_colapsado, rx.text("Usuarios")),
                        variant=rx.cond(State.menu_activo == "admin", "solid", "ghost"),
                        on_click=lambda: State.set_menu("admin"),
                        width="100%", justify="start",
                    ),
                    rx.button(
                        rx.icon("box", size=20),
                        rx.cond(~State.sidebar_colapsado, rx.text("Inventario")),
                        variant=rx.cond(State.menu_activo == "inventario", "solid", "ghost"),
                        on_click=lambda: State.set_menu("inventario"),
                        width="100%", justify="start",
                    ),
                    width="100%", spacing="2"
                )
            ),
            width="100%", spacing="2", margin_top="1em"
        ),
        rx.spacer(),
        rx.divider(),
        rx.hstack(
            rx.icon("user", size=18),
            rx.cond(
                ~State.sidebar_colapsado,
                rx.vstack(
                    rx.text(State.usuario_actual, size="2", weight="bold"),
                    rx.text(State.direccion_actual, size="1", color="gray", truncate=True),
                    align_items="start", spacing="0"
                )
            ),
            rx.spacer(),
            rx.button(rx.icon("log-out", size=16), color_scheme="red", variant="ghost", on_click=State.cerrar_sesion),
            width="100%", align="center", padding_top="1em"
        ),
        height="100vh",
        width=rx.cond(State.sidebar_colapsado, "70px", "260px"),
        padding="1em",
        border_right="1px solid var(--gray-5)",
        style={"transition": "width 0.2s ease-in-out"},
    )

def render_burbuja_chat(msg: dict[str, Any]) -> rx.Component:
    es_soporte = msg["es_soporte"]
    return rx.hstack(
        rx.vstack(
            rx.hstack(
                rx.text(msg["emisor"], weight="bold", size="2"),
                rx.text(msg["fecha"], size="1", color="gray"),
                spacing="2",
            ),
            rx.text(msg["mensaje"], size="2"),
            align_items=rx.cond(es_soporte, "start", "end"),
            background_color=rx.cond(es_soporte, "var(--gray-3)", "var(--blue-3)"),
            border=rx.cond(es_soporte, "1px solid var(--gray-5)", "1px solid var(--blue-5)"),
            padding="0.8em 1.2em", border_radius="12px", max_width="85%",
        ),
        justify=rx.cond(es_soporte, "start", "end"),
        width="100%", margin_y="0.3em",
    )

def vista_chat_modulo() -> rx.Component:
    """Módulo de Chat Responsive Centrado con Globos/Pestañas y Saludo Institucional."""
    return rx.center(
        rx.vstack(
            # --- Encabezado Saludo Institucional ---
            rx.card(
                rx.hstack(
                    rx.icon("bell-ring", size=32, color="var(--blue-9)"),
                    rx.vstack(
                        rx.heading(f"¡Hola, {State.usuario_actual}!", size="4"),
                        rx.text("Estamos atentos a su solicitud de Soporte Técnico y Sistemas", size="3", color="var(--blue-11)", weight="medium"),
                        rx.text(f"Dirección: {State.direccion_actual}", size="1", color="gray"),
                        align_items="start", spacing="1",
                    ),
                    align="center", spacing="3", width="100%"
                ),
                width="100%", padding="1.2em", margin_bottom="1em",
                style={"border-left": "5px solid var(--blue-9)"}
            ),

            # --- Globos / Botones de Control de Pestañas ---
            rx.hstack(
                rx.button(
                    rx.icon("history", size=18),
                    "Revisar Mensajes y Estatus Último Ticket",
                    variant=rx.cond(State.pestana_chat_activa == "historial", "solid", "soft"),
                    color_scheme="blue",
                    border_radius="20px",
                    on_click=lambda: State.set_pestana_chat("historial"),
                    size="3", width="50%"
                ),
                rx.button(
                    rx.icon("send", size=18),
                    "Enviar Mensaje / Chatear con Técnico",
                    variant=rx.cond(State.pestana_chat_activa == "nuevo", "solid", "soft"),
                    color_scheme="green",
                    border_radius="20px",
                    on_click=lambda: State.set_pestana_chat("nuevo"),
                    size="3", width="50%"
                ),
                spacing="3", width="100%", margin_bottom="1.5em",
                columns=rx.breakpoints(initial="1", sm="2")
            ),

            # --- Contenido según Globo Seleccionado ---
            rx.cond(
                State.pestana_chat_activa == "historial",
                # GLOBO 1: HISTORIAL Y ESTATUS ÚLTIMO TICKET
                rx.vstack(
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.badge("Estatus de su última solicitud", color_scheme="gray"),
                                rx.spacer(),
                                rx.badge(
                                    State.ultima_solicitud_usuario["estado"],
                                    color_scheme=rx.match(
                                        State.ultima_solicitud_usuario["estado"],
                                        ("En Proceso", "yellow"),
                                        ("En Progreso", "orange"),
                                        ("Hecho", "green"),
                                        "gray"
                                    ),
                                    size="2"
                                ),
                                width="100%", align="center"
                            ),
                            rx.heading(State.ultima_solicitud_usuario["asunto"], size="3"),
                            rx.text(State.ultima_solicitud_usuario["mensaje"], size="2", color="gray"),
                            rx.cond(
                                State.ultima_solicitud_usuario["nota_tecnica"] != "",
                                rx.callout(
                                    f"Respuesta Técnica: {State.ultima_solicitud_usuario['nota_tecnica']}",
                                    icon="check-circle", color_scheme="green", margin_top="0.5em"
                                )
                            ),
                            align_items="start", width="100%", spacing="2"
                        ),
                        width="100%", padding="1em", margin_bottom="1em"
                    ),
                    rx.heading("Historial de Interacción por Chat", size="3", margin_bottom="0.5em"),
                    rx.box(
                        rx.vstack(rx.foreach(State.historial_chat, render_burbuja_chat), width="100%"),
                        height="320px", overflow_y="auto", padding="1em",
                        border="1px solid var(--gray-5)", border_radius="12px", width="100%"
                    ),
                    width="100%"
                ),
                # GLOBO 2: NUEVO MENSAJE / CHATEAR CON EL TÉCNICO
                rx.card(
                    rx.vstack(
                        rx.heading("Nueva Solicitud de Soporte Técnico", size="3"),
                        rx.text("Escriba su requerimiento. El equipo de sistemas recibirá una notificación inmediata.", size="2", color="gray"),
                        rx.text("Asunto / Tipo de Falla (Opcional):", size="2", weight="bold"),
                        rx.input(
                            placeholder="Ej: Impresora no conecta / Fallo de internet",
                            value=State.asunto_chat_temp,
                            on_change=State.set_asunto_chat_temp,
                            width="100%"
                        ),
                        rx.text("Mensaje para el Técnico:", size="2", weight="bold"),
                        rx.text_area(
                            placeholder="Describa detalladamente el problema o solicitud...",
                            value=State.nuevo_mensaje_chat,
                            on_change=State.set_nuevo_mensaje_chat,
                            rows="5", width="100%"
                        ),
                        rx.button(
                            rx.icon("send", size=18),
                            "Enviar Solicitud con Notificación",
                            color_scheme="green",
                            size="3",
                            on_click=State.enviar_mensaje_chat,
                            width="100%", margin_top="1em"
                        ),
                        align_items="start", spacing="2", width="100%"
                    ),
                    padding="1.5em", width="100%"
                )
            ),
            max_width="750px", width="100%", align="center"
        ),
        width="100%", padding="1em"
    )

def vista_autenticacion() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("headset", size=32),
                    rx.heading("Soporte Técnico", size="6"),
                    align="center", margin_bottom="1em"
                ),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Iniciar Sesión", value="login"),
                        rx.tabs.trigger("Registrarse", value="register"),
                        rx.tabs.trigger("Recuperar Clave", value="reset"),
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.text("Usuario", size="2", weight="bold"),
                            rx.input(placeholder="Ej: admin o solicitante", value=State.login_user, on_change=State.set_login_user, width="100%"),
                            rx.text("Contraseña", size="2", weight="bold"),
                            rx.input(type="password", placeholder="••••••••", value=State.login_pass, on_change=State.set_login_pass, width="100%"),
                            rx.cond(State.login_error != "", rx.callout(State.login_error, icon="triangle_alert", color_scheme="red", width="100%")),
                            rx.button("Ingresar al Sistema", on_click=State.iniciar_sesion, width="100%", color_scheme="blue", margin_top="1em"),
                            spacing="2", padding_top="1em"
                        ),
                        value="login"
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.text("Nombre Completo", size="2", weight="bold"),
                            rx.input(placeholder="Ej: Juan Pérez", value=State.reg_nombre, on_change=State.set_reg_nombre, width="100%"),
                            rx.text("Usuario", size="2", weight="bold"),
                            rx.input(placeholder="Ej: jperez", value=State.reg_user, on_change=State.set_reg_user, width="100%"),
                            rx.text("Contraseña", size="2", weight="bold"),
                            rx.input(type="password", placeholder="••••••••", value=State.reg_pass, on_change=State.set_reg_pass, width="100%"),
                            rx.text("Dirección Municipal", size="2", weight="bold"),
                            rx.select(DIRECCIONES, value=State.reg_direccion, on_change=State.set_reg_direccion, width="100%"),
                            rx.cond(State.reg_error != "", rx.callout(State.reg_error, icon="triangle_alert", color_scheme="red", width="100%")),
                            rx.cond(State.reg_exito != "", rx.callout(State.reg_exito, icon="check", color_scheme="green", width="100%")),
                            rx.button("Crear Cuenta", on_click=State.registrar_usuario, width="100%", color_scheme="green", margin_top="1em"),
                            spacing="2", padding_top="1em"
                        ),
                        value="register"
                    ),
                    rx.tabs.content(
                        rx.vstack(
                            rx.text("Usuario Registrado", size="2", weight="bold"),
                            rx.input(placeholder="Ingresa tu usuario", value=State.reset_user, on_change=State.set_reset_user, width="100%"),
                            rx.text("Nueva Contraseña", size="2", weight="bold"),
                            rx.input(type="password", placeholder="Nueva clave", value=State.reset_pass, on_change=State.set_reset_pass, width="100%"),
                            rx.cond(State.reset_msg != "", rx.callout(State.reset_msg, icon="info", color_scheme="blue", width="100%")),
                            rx.button("Actualizar Contraseña", on_click=State.recuperar_contrasena, width="100%", color_scheme="orange", margin_top="1em"),
                            spacing="2", padding_top="1em"
                        ),
                        value="reset"
                    ),
                    default_value="login", width="100%"
                ),
                width="350px", align="center"
            ),
            padding="2em"
        ),
        min_height="100vh", width="100%"
    )

def modal_impresion_ticket() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(f"Ficha Técnica de Servicio - Ticket #{State.ticket_seleccionado['id']}"),
            rx.vstack(
                rx.hstack(
                    rx.badge(State.ticket_seleccionado["estado"], color_scheme="blue", size="2"),
                    rx.spacer(),
                    rx.text(f"Fecha: {State.ticket_seleccionado['fecha']}", size="2", color="gray"),
                    width="100%"
                ),
                rx.divider(),
                rx.vstack(
                    rx.text("Solicitante:", weight="bold"),
                    rx.text(State.ticket_seleccionado["usuario_nombre"]),
                    rx.text("Dirección Municipal:", weight="bold"),
                    rx.text(State.ticket_seleccionado["direccion"]),
                    rx.text("Asunto:", weight="bold"),
                    rx.text(State.ticket_seleccionado["asunto"]),
                    rx.text("Detalle de la Solicitud:", weight="bold"),
                    rx.callout(State.ticket_seleccionado["mensaje"], icon="file-text"),
                    align_items="start", width="100%", spacing="2"
                ),
                rx.divider(),
                rx.cond(
                    State.es_admin,
                    rx.vstack(
                        rx.text("Observaciones / Informe Técnico:", weight="bold"),
                        rx.text_area(
                            placeholder="Escribe la solución técnica aplicada...",
                            value=State.nota_tecnica_temp,
                            on_change=State.set_nota_tecnica_temp,
                            width="100%"
                        ),
                        rx.button("Guardar Observación", on_click=State.guardar_nota_tecnica, size="1", color_scheme="blue"),
                        width="100%", align_items="start"
                    ),
                    rx.cond(
                        State.ticket_seleccionado["nota_tecnica"] != "",
                        rx.vstack(
                            rx.text("Informe del Técnico:", weight="bold"),
                            rx.callout(State.ticket_seleccionado["nota_tecnica"], icon="check-circle", color_scheme="green"),
                            width="100%", align_items="start"
                        )
                    )
                ),
                rx.hstack(
                    rx.button("Imprimir Ficha", icon="printer", color_scheme="green", on_click=rx.window_alert("Generando vista de impresión...")),
                    rx.dialog.close(
                        rx.button("Cerrar", color_scheme="gray", variant="soft", on_click=State.cerrar_modal_impresion)
                    ),
                    justify="end", width="100%", margin_top="1em"
                ),
                spacing="3"
            ),
            max_width="500px"
        ),
        open=State.modal_impresion_abierto
    )

def vista_reportes_analitica() -> rx.Component:
    return rx.vstack(
        rx.heading("Módulo de Reportes y Estadísticas Generales", size="5"),
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.heading("Distribución de Solicitudes por Estado", size="3"),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(data_key="cantidad", fill="#3b82f6"),
                        rx.recharts.x_axis(data_key="estado"),
                        rx.recharts.y_axis(),
                        rx.recharts.tooltip(),
                        data=State.datos_grafico_estados,
                        width="100%", height=250,
                    ),
                    width="100%"
                ),
                padding="1.5em"
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Resumen Ejecutivo de Gestión", size="3"),
                    rx.text("• Total de solicitudes procesadas: ", rx.text.span(State.total_tickets, weight="bold")),
                    rx.text("• Tasa de solución efectiva: ", rx.text.span(State.tasa_solucion, weight="bold", color="green")),
                    rx.text("• Direcciones atendidas activamente: ", rx.text.span("15 Direcciones", weight="bold")),
                    rx.divider(),
                    rx.button(
                        rx.icon("download"), "Exportar Informe Consolidado (CSV)",
                        color_scheme="green", on_click=rx.window_alert("Exportando reporte general a CSV...")
                    ),
                    align_items="start", spacing="3", width="100%"
                ),
                padding="1.5em"
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="4", width="100%", margin_top="1em"
        ),
        width="100%"
    )

def render_fila_usuario(user: dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(user["user"]),
        rx.table.cell(user["nombre"]),
        rx.table.cell(user["direccion"]),
        rx.table.cell(
            rx.badge(
                rx.cond(user["es_admin"], "Administrador", "Solicitante"),
                color_scheme=rx.cond(user["es_admin"], "purple", "blue")
            )
        ),
        rx.table.cell(
            rx.button(
                rx.cond(user["es_admin"], "Quitar Admin", "Hacer Admin"),
                size="1", color_scheme=rx.cond(user["es_admin"], "red", "green"),
                on_click=lambda: State.cambiar_rol_usuario(user["user"])
            )
        )
    )

def vista_admin_usuarios() -> rx.Component:
    return rx.vstack(
        rx.heading("Gestión y Permisos de Usuarios", size="5"),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Usuario"),
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Dirección"),
                    rx.table.column_header_cell("Rol Actual"),
                    rx.table.column_header_cell("Acciones"),
                )
            ),
            rx.table.body(rx.foreach(State.usuarios_registrados, render_fila_usuario)),
            width="100%"
        ),
        width="100%"
    )

def render_fila_inventario(item: dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item["codigo"]),
        rx.table.cell(item["nombre"]),
        rx.table.cell(item["categoria"]),
        rx.table.cell(item["cantidad"]),
        rx.table.cell(item["estado"]),
    )

def vista_inventario() -> rx.Component:
    return rx.vstack(
        rx.heading("Inventario de Componentes y Piezas", size="5"),
        rx.card(
            rx.vstack(
                rx.heading("Agregar Nuevo Componente", size="3"),
                rx.hstack(
                    rx.input(placeholder="Código (Ej: RAM-001)", value=State.inv_codigo, on_change=State.set_inv_codigo),
                    rx.input(placeholder="Nombre del componente", value=State.inv_nombre, on_change=State.set_inv_nombre),
                    rx.select(["Periféricos", "Memorias", "Almacenamiento", "Procesadores", "Redes"], value=State.inv_categoria, on_change=State.set_inv_categoria),
                    rx.input(type="number", placeholder="Cantidad", value=State.inv_cantidad.to(str), on_change=State.set_inv_cantidad, width="100px"),
                    rx.button("Agregar", on_click=State.agregar_item_inventario, color_scheme="green"),
                    wrap="wrap", spacing="2"
                ),
                width="100%"
            ),
            width="100%", margin_bottom="1.5em"
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Código"),
                    rx.table.column_header_cell("Nombre"),
                    rx.table.column_header_cell("Categoría"),
                    rx.table.column_header_cell("Stock"),
                    rx.table.column_header_cell("Estado"),
                )
            ),
            rx.table.body(rx.foreach(State.inventario, render_fila_inventario)),
            width="100%"
        ),
        width="100%"
    )

def tarjeta_estadistica(titulo: str, valor: rx.Var, icono: str, color_bg: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color="gray"),
                rx.heading(valor, size="6"),
                align_items="start",
            ),
            rx.spacer(),
            rx.icon(tag=icono, size=28),
            width="100%", align="center",
        ),
        style={"background": color_bg}, width="100%",
    )

def botonera_filtros() -> rx.Component:
    return rx.flex(
        rx.button("Todos", color_scheme="gray", variant=rx.cond(State.filtro_estado == "Todos", "solid", "outline"), on_click=lambda: State.cambiar_filtro("Todos")),
        rx.button("Mis Tickets", color_scheme="blue", variant=rx.cond(State.filtro_estado == "Mis Tickets", "solid", "outline"), on_click=lambda: State.cambiar_filtro("Mis Tickets")),
        rx.button("En Proceso", color_scheme="yellow", variant=rx.cond(State.filtro_estado == "En Proceso", "solid", "outline"), on_click=lambda: State.cambiar_filtro("En Proceso")),
        rx.button("En Progreso", color_scheme="orange", variant=rx.cond(State.filtro_estado == "En Progreso", "solid", "outline"), on_click=lambda: State.cambiar_filtro("En Progreso")),
        rx.button("Hechos", color_scheme="green", variant=rx.cond(State.filtro_estado == "Hecho", "solid", "outline"), on_click=lambda: State.cambiar_filtro("Hecho")),
        spacing="2", wrap="wrap", margin_bottom="1em"
    )

def render_fila_ticket(ticket: dict[str, Any]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(ticket["id"]),
        rx.table.cell(ticket["usuario_nombre"]),
        rx.table.cell(ticket["direccion"]),
        rx.table.cell(ticket["asunto"]),
        rx.table.cell(
            rx.cond(
                State.es_admin,
                rx.select(
                    ["En Proceso", "En Progreso", "Hecho"],
                    value=ticket["estado"],
                    on_change=lambda val: State.cambiar_estado_ticket(ticket["id"], val),
                    size="1"
                ),
                rx.badge(
                    ticket["estado"],
                    color_scheme=rx.match(ticket["estado"], ("En Proceso", "yellow"), ("En Progreso", "orange"), ("Hecho", "green"), "gray")
                )
            )
        ),
        rx.table.cell(ticket["fecha"]),
        rx.table.cell(
            rx.button(
                rx.icon("printer", size=16), color_scheme="purple", size="1", variant="soft",
                on_click=lambda: State.ver_detalle_ticket(ticket)
            )
        )
    )

def vista_dashboard_tickets() -> rx.Component:
    return rx.vstack(
        rx.grid(
            tarjeta_estadistica("Total Solicitudes", State.total_tickets, "ticket", "var(--accent-2)"),
            tarjeta_estadistica("En Proceso", State.total_en_proceso, "clock", "var(--yellow-2)"),
            tarjeta_estadistica("En Progreso", State.total_en_progreso, "loader-circle", "var(--orange-2)"),
            tarjeta_estadistica("Hechos", State.total_hechos, "circle-check", "var(--green-2)"),
            columns=rx.breakpoints(initial="1", sm="2", md="4"),
            spacing="4", width="100%", margin_bottom="2em"
        ),
        rx.heading("Gestión General de Solicitudes", size="5"),
        botonera_filtros(),
        rx.hstack(
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Buscar por usuario o mensaje...",
                value=State.busqueda,
                on_change=State.set_busqueda,
                width="100%"
            ),
            rx.select(
                ["Todas"] + DIRECCIONES,
                value=State.filtro_direccion,
                on_change=State.set_filtro_direccion,
                placeholder="Filtrar por Dirección",
                width="300px"
            ),
            width="100%", spacing="3", margin_bottom="1em"
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("ID"),
                    rx.table.column_header_cell("Usuario"),
                    rx.table.column_header_cell("Dirección"),
                    rx.table.column_header_cell("Asunto"),
                    rx.table.column_header_cell("Estado"),
                    rx.table.column_header_cell("Fecha"),
                    rx.table.column_header_cell("Acciones"),
                )
            ),
            rx.table.body(rx.foreach(State.tickets_paginados, render_fila_ticket)),
            width="100%"
        ),
        rx.hstack(
            rx.button("Anterior", on_click=State.pagina_anterior, disabled=State.pagina_actual == 1),
            rx.text(f"Página {State.pagina_actual} de {State.total_paginas}"),
            rx.button("Siguiente", on_click=State.pagina_siguiente, disabled=State.pagina_actual == State.total_paginas),
            justify="between", align="center", width="100%", margin_top="1em"
        ),
        width="100%"
    )

def layout_principal() -> rx.Component:
    return rx.cond(
        State.logged_in,
        rx.hstack(
            panel_lateral_sidebar(),
            rx.box(
                rx.match(
                    State.menu_activo,
                    ("chat", vista_chat_modulo()),
                    ("dashboard", vista_dashboard_tickets()),
                    ("reportes", vista_reportes_analitica()),
                    ("admin", vista_admin_usuarios()),
                    ("inventario", vista_inventario()),
                    vista_chat_modulo()
                ),
                width="100%", padding="1.5em", overflow_y="auto", height="100vh"
            ),
            modal_impresion_ticket(),
            width="100%", height="100vh", spacing="0"
        ),
        vista_autenticacion()
    )

# ==========================================
# 4. CONFIGURACIÓN DE LA APP
# ==========================================

app = rx.App()
app.add_page(layout_principal, route="/", title="Soporte Técnico | Autogestión")