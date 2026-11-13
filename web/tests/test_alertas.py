"""Tests de alertas: ver, atender, deshacer, simular y la prueba de Telegram."""
from datetime import datetime

import app as app_modulo

FECHA = datetime(2026, 11, 4, 20, 30)


# ---------- Ver alertas ----------

def test_alertas_lista(cliente, base):
    # (id, robot, tipo, descripcion, fecha_hora, atendida)
    base.todos = [[
        (1, "Mini Protud", "movimiento", "Pasillo", FECHA, False),
        (2, "Mini Protud", "obstaculo", "Puerta", FECHA, True),
    ]]
    respuesta = cliente.get("/alertas")
    assert respuesta.status_code == 200
    assert b"Alerta #1" in respuesta.data


def test_alertas_vacia(cliente, base):
    base.todos = [[]]
    assert cliente.get("/alertas").status_code == 200


def test_alertas_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.get("/alertas").status_code == 500


# ---------- Atender y deshacer ----------

def test_atender_alerta(cliente, base):
    respuesta = cliente.post("/alertas/5/atender")

    # Después de atender, vuelve a la lista de alertas
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/alertas")
    # Se mandó el UPDATE con el número de alerta correcto
    sql, parametros = base.consultas[0]
    assert "atendida = TRUE" in sql
    assert parametros == (5,)


def test_atender_alerta_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.post("/alertas/5/atender").status_code == 500


def test_deshacer_alerta(cliente, base):
    respuesta = cliente.post("/alertas/5/deshacer")
    assert respuesta.status_code == 302
    sql, parametros = base.consultas[0]
    assert "atendida = FALSE" in sql
    assert parametros == (5,)


def test_deshacer_alerta_si_falla_la_base(cliente, base):
    base.falla = True
    assert cliente.post("/alertas/5/deshacer").status_code == 500


# ---------- Simular alerta (guarda + Telegram + registra) ----------

def test_simular_alerta(cliente, base, monkeypatch):
    # No mandamos nada a Telegram de verdad: fingimos que salió bien
    monkeypatch.setattr(app_modulo, "enviar_foto_telegram", lambda **datos: True)
    # 1er fetchone: id de la alerta nueva / 2do: id de la notificación
    base.uno = [(7,), (3,)]

    respuesta = cliente.post("/simular-alerta")

    assert respuesta.status_code == 201
    assert respuesta.get_json() == {
        "alerta_id": 7,
        "registrada": True,
        "telegram_enviado": True,
    }
    # La notificación quedó registrada como "enviada"
    sql, parametros = base.consultas[1]
    assert parametros == (7, "Mini Protud detectó movimiento (SIMULACIÓN)", "enviada")


def test_registrar_notificacion_fallida(base):
    base.uno = [(9,)]
    nuevo_id = app_modulo.registrar_notificacion(1, "Prueba", enviado=False)
    assert nuevo_id == 9
    assert base.consultas[0][1] == (1, "Prueba", "fallida")


def test_simular_alerta_si_falla_la_base(cliente, base):
    base.falla = True
    respuesta = cliente.post("/simular-alerta")
    assert respuesta.status_code == 500
    assert "error" in respuesta.get_json()


# ---------- Probar Telegram desde Flask ----------

def test_probar_telegram_ok(cliente, monkeypatch):
    monkeypatch.setattr(app_modulo, "enviar_alerta_telegram", lambda **datos: True)
    respuesta = cliente.get("/probar-telegram")
    assert respuesta.status_code == 200
    assert "correctamente".encode() in respuesta.data


def test_probar_telegram_falla(cliente, monkeypatch):
    monkeypatch.setattr(app_modulo, "enviar_alerta_telegram", lambda **datos: False)
    assert cliente.get("/probar-telegram").status_code == 500
