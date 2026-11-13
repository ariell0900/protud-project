"""
Preparativos que comparten todos los tests de PROTUD.

pytest lee este archivo solo (no hace falta importarlo).
Acá armamos dos cosas:
  1. "cliente": un navegador de prueba de Flask.
  2. "base": una base de datos FALSA, para no tocar la PostgreSQL de verdad.
"""
import sys
from pathlib import Path

import psycopg
import pytest

# Permitir importar app.py y telegram_service.py desde la carpeta web/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_modulo  # noqa: E402  (el módulo entero, para poder reemplazar cosas)


class CursorFalso:
    """Hace de cursor de PostgreSQL: anota las consultas y devuelve datos preparados."""

    def __init__(self, base):
        self.base = base

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parametros=None):
        # Guardamos lo que se ejecutó para poder revisarlo en el test
        self.base.consultas.append((sql, parametros))

    def fetchone(self):
        # Devuelve el siguiente resultado de la lista "uno"
        return self.base.uno.pop(0)

    def fetchall(self):
        # Devuelve el siguiente resultado de la lista "todos"
        return self.base.todos.pop(0)


class ConexionFalsa:
    """Hace de conexión: solo sabe abrir cursores falsos."""

    def __init__(self, base):
        self.base = base

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return CursorFalso(self.base)


class BaseFalsa:
    """
    Reemplaza a conectar_db().

    - uno:   lista de respuestas para fetchone()  (en orden)
    - todos: lista de respuestas para fetchall()  (en orden)
    - falla: si es True, simula que PostgreSQL está caído
    """

    def __init__(self):
        self.uno = []
        self.todos = []
        self.consultas = []
        self.falla = False

    def conectar(self):
        if self.falla:
            raise psycopg.Error("PostgreSQL simulado caído")
        return ConexionFalsa(self)


@pytest.fixture
def cliente():
    """Navegador de prueba de Flask."""
    app_modulo.app.config["TESTING"] = True
    # Si no hay .env (por ejemplo en otra compu), ponemos una clave de prueba
    if not app_modulo.app.secret_key:
        app_modulo.app.secret_key = "clave-solo-para-tests"
    return app_modulo.app.test_client()


@pytest.fixture
def base(monkeypatch):
    """Base de datos falsa: reemplaza conectar_db solo durante el test."""
    base_falsa = BaseFalsa()
    monkeypatch.setattr(app_modulo, "conectar_db", base_falsa.conectar)
    return base_falsa


@pytest.fixture
def como_admin(cliente):
    """Deja la sesión iniciada como administrador."""
    with cliente.session_transaction() as sesion:
        sesion["usuario"] = {"id": 1, "nombre": "Ariel", "rol": "administrador"}
    return cliente
