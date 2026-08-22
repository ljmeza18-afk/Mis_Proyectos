import reflex as rx
import os

config = rx.Config(
    app_name="bd_prueba",
    db_url=os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/bd_prueba",
    ),
)
