"""Tests del login con Google y de la página de usuarios (solo administrador)."""
from flask import redirect

import app as app_modulo


# ---------- Login con Google ----------

def test_login_google_manda_a_google(cliente, monkeypatch):
    # No vamos a Google de verdad: fingimos la redirección
    monkeypatch.setattr(app_modulo.google, "authorize_redirect",
                        lambda url: redirect("https://accounts.google.com/falso"))
    respuesta = cliente.get("/login/google")
    assert respuesta.status_code == 302
    assert "accounts.google.com" in respuesta.headers["Location"]


def fingir_google(monkeypatch):
    """Google 'responde' con los datos de una persona de prueba."""
    monkeypatch.setattr(app_modulo.google, "authorize_access_token",
                        lambda: {"userinfo": {"name": "Ariel", "email": "ariel@prueba.com"}})


def test_callback_usuario_activo_entra_al_panel(cliente, base, monkeypatch):
    fingir_google(monkeypatch)
    base.uno = [(1, "operador", True)]  # (id, rol, activo)

    respuesta = cliente.get("/callback")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/panel")
    with cliente.session_transaction() as sesion:
        assert sesion["usuario"]["email"] == "ariel@prueba.com"


def test_callback_usuario_dado_de_baja(cliente, base, monkeypatch):
    fingir_google(monkeypatch)
    base.uno = [(1, "operador", False)]
    assert cliente.get("/callback").status_code == 403


def test_callback_si_falla_la_base(cliente, base, monkeypatch):
    fingir_google(monkeypatch)
    base.falla = True
    assert cliente.get("/callback").status_code == 500


# ---------- Usuarios: sin permiso ----------

def test_usuarios_sin_sesion_no_entra(cliente):
    assert cliente.get("/usuarios").status_code == 403


def test_baja_sin_permiso(cliente):
    assert cliente.post("/usuarios/2/baja").status_code == 403


def test_reactivar_sin_permiso(cliente):
    assert cliente.post("/usuarios/2/reactivar").status_code == 403


# ---------- Usuarios: como administrador ----------

def test_usuarios_lista_como_admin(como_admin, base):
    # (id, nombre, email, rol, activo)
    base.todos = [[
        (1, "Ariel", "ariel@prueba.com", "administrador", True),
        (2, "Lauti", "lauti@prueba.com", "operador", False),
    ]]
    respuesta = como_admin.get("/usuarios")
    assert respuesta.status_code == 200
    assert b"lauti@prueba.com" in respuesta.data


def test_baja_usuario(como_admin, base):
    respuesta = como_admin.post("/usuarios/2/baja")
    assert respuesta.status_code == 302
    sql, parametros = base.consultas[0]
    assert "activo = FALSE" in sql
    assert parametros == (2,)


def test_reactivar_usuario(como_admin, base):
    respuesta = como_admin.post("/usuarios/2/reactivar")
    assert respuesta.status_code == 302
    sql, parametros = base.consultas[0]
    assert "activo = TRUE" in sql
    assert parametros == (2,)
