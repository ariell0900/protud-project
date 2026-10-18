import sys
from pathlib import Path

# Permitir importar la aplicación de PROTUD
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app


def test_pagina_principal():
    # Crear un navegador de prueba de Flask
    cliente = app.test_client()

    # Simular una visita a la página principal
    respuesta = cliente.get("/")

    # Comprobar que la página responde correctamente
    assert respuesta.status_code == 200

    # Comprobar que aparece el nombre del proyecto
    assert b"PROTUD" in respuesta.data