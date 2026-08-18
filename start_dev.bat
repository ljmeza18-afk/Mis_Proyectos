@echo off
echo Limpiando el entorno de desarrollo...
if exist .web (
    rmdir /s /q .web
)
echo Iniciando la aplicacion...
reflex run
