"""
Tests del Sistema de Chat de Protud.
No usan la base de datos real: la reemplazamos por una "falsa" (mock),
así los tests andan en cualquier compu y no ensucian la base.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Para poder importar app.py desde la carpeta web
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app

# Usuarios de prueba: uno común y uno administrador
USUARIO = {"id": 1, "nombre": "Ariel", "email": "a@gmail.com", "rol": "operador"}
ADMIN = {"id": 2, "nombre": "Admin", "email": "b@gmail.com", "rol": "administrador"}


def cliente(usuario=None):
    """Crea un navegador de prueba; si le pasamos un usuario, inicia sesión."""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "clave-de-prueba"
    c = app.test_client()
    if usuario:
        with c.session_transaction() as sesion:
            sesion["usuario"] = usuario
    return c


def cursor_falso(mock_conectar):
    """Devuelve el cursor falso que usa app.py adentro de los 'with'."""
    conexion = mock_conectar.return_value.__enter__.return_value
    return conexion.cursor.return_value.__enter__.return_value


# 1) Sin iniciar sesión, el chat te manda al login
def test_chat_sin_sesion_redirige_al_login():
    respuesta = cliente().get("/chat")
    assert respuesta.status_code == 302
    assert "/login/google" in respuesta.headers["Location"]


# 2) Con sesión, muestra los mensajes del robot
@patch("app.conectar_db")
def test_chat_muestra_mensajes(mock_conectar):
    cursor = cursor_falso(mock_conectar)
    cursor.fetchall.side_effect = [
        [(1, "Mini Protud")],                                              # robots
        [(10, "Hola equipo", datetime(2026, 11, 10, 20, 0), "Ariel", 1)],  # mensajes
    ]
    respuesta = cliente(USUARIO).get("/chat?robot=1")
    assert respuesta.status_code == 200
    assert "Hola equipo" in respuesta.get_data(as_text=True)


# 3) Mandar un mensaje lo guarda en la base
@patch("app.conectar_db")
def test_enviar_mensaje_lo_guarda(mock_conectar):
    cursor = cursor_falso(mock_conectar)
    respuesta = cliente(USUARIO).post("/chat", data={"robot": 1, "texto": "Voy al pasillo 2"})
    assert respuesta.status_code == 302
    sql, valores = cursor.execute.call_args[0]
    assert "INSERT INTO mensajes" in sql
    assert valores == (1, 1, "Voy al pasillo 2")


# 4) Un mensaje vacío no se guarda
@patch("app.conectar_db")
def test_mensaje_vacio_no_se_guarda(mock_conectar):
    cursor = cursor_falso(mock_conectar)
    cliente(USUARIO).post("/chat", data={"robot": 1, "texto": "   "})
    cursor.execute.assert_not_called()


# 5) Un operador solo puede borrar sus propios mensajes
@patch("app.conectar_db")
def test_operador_borra_solo_lo_suyo(mock_conectar):
    cursor = cursor_falso(mock_conectar)
    cliente(USUARIO).post("/chat/mensajes/10/borrar", data={"robot": 1})
    sql, valores = cursor.execute.call_args[0]
    assert "usuario_id" in sql
    assert valores == (10, 1)


# 6) El administrador puede borrar cualquier mensaje
@patch("app.conectar_db")
def test_admin_borra_cualquiera(mock_conectar):
    cursor = cursor_falso(mock_conectar)
    cliente(ADMIN).post("/chat/mensajes/10/borrar", data={"robot": 1})
    sql, valores = cursor.execute.call_args[0]
    assert "usuario_id" not in sql
    assert valores == (10,)