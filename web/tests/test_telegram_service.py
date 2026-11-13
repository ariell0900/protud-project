"""Tests de telegram_service.py sin mandar mensajes de verdad."""
# No mandamos nada real: simulamos la base y simulamos a Telegram.
# Así los tests son rápidos y no gastan el bot.
import requests

import telegram_service

class RespuestaFalsa:
    """Imita lo que devuelve Telegram cuando todo sale bien."""
    # status_code 200 = Telegram aceptó el mensaje
    # Lo agregamos porque telegram_service.py revisa r.status_code == 200
    status_code = 200

    def raise_for_status(self):
        pass  # todo bien, sin errores HTTP

    def json(self):
        return {"ok": True}

def poner_claves(monkeypatch):
    # Simula que el .env tiene TOKEN y CHAT_ID
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")

def sin_claves(monkeypatch):
    # Simula que el .env está vacío / sin TOKEN
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

def internet_caido(*args, **kwargs):
    # Simula que no hay internet: requests.post tira este error
    raise requests.ConnectionError("sin internet")

def con_suscriptores(monkeypatch):
    # Truco clave: en vez de usar la base de verdad,
    # le decimos a obtener_suscriptores() que devuelva [123]
    # Así probamos el envío sin necesitar PostgreSQL
    monkeypatch.setattr(telegram_service, "obtener_suscriptores", lambda: [123])

# ---------- enviar_alerta_telegram ----------

def test_alerta_sin_claves(monkeypatch):
    sin_claves(monkeypatch)
    # Si no hay nadie suscripto, no hay a quién mandar -> False
    monkeypatch.setattr(telegram_service, "obtener_suscriptores", lambda: [])
    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is False

def test_alerta_enviada(monkeypatch):
    poner_claves(monkeypatch)
    con_suscriptores(monkeypatch)  # Simulamos 1 suscriptor
    enviados = []

    def post_falso(url, json=None, data=None, timeout=None, **kwargs):
        # Guarda lo que se iba a mandar, para revisarlo después
        # json or data: porque alerta usa json= y foto usa data=
        enviados.append(json or data)
        return RespuestaFalsa()  # Hace de cuenta que Telegram dijo 200

    # Reemplazamos requests.post de verdad por nuestro post_falso
    monkeypatch.setattr(telegram_service.requests, "post", post_falso)

    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is True
    # El mensaje lleva el nombre del robot
    assert "Mini Protud" in enviados[0]["text"]

def test_alerta_sin_internet(monkeypatch):
    poner_claves(monkeypatch)
    con_suscriptores(monkeypatch)
    # Simulamos internet caído
    monkeypatch.setattr(telegram_service.requests, "post", internet_caido)
    # Tiene que devolver False, no romper con error
    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is False

# ---------- enviar_foto_telegram ----------

def test_foto_sin_claves(monkeypatch, tmp_path):
    sin_claves(monkeypatch)
    monkeypatch.setattr(telegram_service, "obtener_suscriptores", lambda: [])
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", tmp_path / "x.jpg") is False

def test_foto_enviada(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    con_suscriptores(monkeypatch)
    # tmp_path: carpeta temporal que pytest crea y borra sola
    foto = tmp_path / "prueba.jpeg"
    foto.write_bytes(b"imagen de prueba")  # una "foto" de mentira
    # Simulamos que Telegram responde 200
    monkeypatch.setattr(telegram_service.requests, "post",
                        lambda *args, **kwargs: RespuestaFalsa())

    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", foto) is True

def test_foto_que_no_existe(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    con_suscriptores(monkeypatch)
    # Esta foto no la creamos, entonces open() va a fallar
    no_existe = tmp_path / "no_existe.jpeg"
    # Tiene que devolver False por el try/except, no romper
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", no_existe) is False

def test_foto_sin_internet(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    con_suscriptores(monkeypatch)
    foto = tmp_path / "prueba.jpeg"
    foto.write_bytes(b"imagen de prueba")
    monkeypatch.setattr(telegram_service.requests, "post", internet_caido)
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", foto) is False