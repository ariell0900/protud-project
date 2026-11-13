"""Tests de las páginas generales: control, fotos, panel, robot, probar-db y notificaciones."""
from datetime import datetime

import app as app_modulo

FECHA = datetime(2026, 11, 4, 20, 30)


# ---------- Páginas simples (no usan la base) ----------

def test_control(cliente):
    respuesta = cliente.get("/control")
    assert respuesta.status_code == 200


def test_fotos_muestra_las_fotos_de_ejemplo(cliente):
    respuesta = cliente.get("/fotos")
    assert respuesta.status_code == 200
    assert "Movimiento detectado".encode() in respuesta.data


# ---------- Panel ----------

def test_panel_muestra_los_numeros(cliente, base):
    # Primer fetchone: (pendientes, últimas 24 h, imágenes)
    base.uno = [(4, 9, 2)]
    # Primer fetchall: las 5 alertas más nuevas
    base.todos = [[(FECHA, "movimiento", False)]]

    respuesta = cliente.get("/panel")

    assert respuesta.status_code == 200
    assert b"04/11/2026 20:30" in respuesta.data


def test_panel_si_falla_la_base(cliente, base):
    base.falla = True
    respuesta = cliente.get("/panel")
    assert respuesta.status_code == 500


# ---------- Robot ----------

def test_robot_con_ultima_alerta(cliente, base):
    base.uno = [("movimiento", "Algo se movió", FECHA, False)]
    respuesta = cliente.get("/robot")
    assert respuesta.status_code == 200
    assert "Algo se movió".encode() in respuesta.data


def test_robot_sin_alertas(cliente, base):
    base.uno = [None]  # la tabla está vacía
    respuesta = cliente.get("/robot")
    assert respuesta.status_code == 200


def test_robot_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.get("/robot").status_code == 500


# ---------- Probar conexión ----------

def test_probar_db_cuenta_robots(cliente, base):
    base.uno = [(3,)]
    respuesta = cliente.get("/probar-db")
    assert respuesta.status_code == 200
    assert b"Robots registrados: 3" in respuesta.data


def test_probar_db_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.get("/probar-db").status_code == 500


# ---------- Notificaciones ----------

def test_notificaciones_lista(cliente, base):
    # (id, mensaje, fecha_envio, leida, alerta_id, estado_envio)
    base.todos = [[
        (1, "Movimiento", FECHA, False, 7, "enviada"),
        (2, "Obstáculo", FECHA, False, 8, "fallida"),
    ]]
    respuesta = cliente.get("/notificaciones")
    assert respuesta.status_code == 200
    assert b"#7" in respuesta.data


def test_notificaciones_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.get("/notificaciones").status_code == 500


# ---------- conectar_db (elige nube o compu) ----------

def test_conectar_db_en_la_nube(monkeypatch):
    llamadas = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://nube/protud")
    monkeypatch.setattr(app_modulo.psycopg, "connect",
                        lambda *args, **kwargs: llamadas.append((args, kwargs)))

    app_modulo.conectar_db()

    # En la nube se conecta con la URL
    assert llamadas[0][0] == ("postgresql://nube/protud",)


def test_conectar_db_en_la_compu(monkeypatch):
    llamadas = []
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_NAME", "protud")
    monkeypatch.setattr(app_modulo.psycopg, "connect",
                        lambda *args, **kwargs: llamadas.append(kwargs))

    app_modulo.conectar_db()

    # En la compu usa los datos sueltos del .env
    assert llamadas[0]["dbname"] == "protud"
