"""Tests de telegram_service.py sin mandar mensajes de verdad."""
import requests

import telegram_service


class RespuestaFalsa:
    """Imita lo que devuelve Telegram."""

    def raise_for_status(self):
        pass  # todo bien, sin errores HTTP

    def json(self):
        return {"ok": True}


def poner_claves(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")


def sin_claves(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)


def internet_caido(*args, **kwargs):
    raise requests.ConnectionError("sin internet")


# ---------- enviar_alerta_telegram ----------

def test_alerta_sin_claves(monkeypatch):
    sin_claves(monkeypatch)
    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is False


def test_alerta_enviada(monkeypatch):
    poner_claves(monkeypatch)
    enviados = []

    def post_falso(url, data, timeout):
        enviados.append(data)
        return RespuestaFalsa()

    monkeypatch.setattr(telegram_service.requests, "post", post_falso)

    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is True
    # El mensaje lleva el nombre del robot
    assert "Mini Protud" in enviados[0]["text"]


def test_alerta_sin_internet(monkeypatch):
    poner_claves(monkeypatch)
    monkeypatch.setattr(telegram_service.requests, "post", internet_caido)
    assert telegram_service.enviar_alerta_telegram("Mini Protud", "Movimiento", "Escuela") is False


# ---------- enviar_foto_telegram ----------

def test_foto_sin_claves(monkeypatch, tmp_path):
    sin_claves(monkeypatch)
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", tmp_path / "x.jpg") is False


def test_foto_enviada(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    foto = tmp_path / "prueba.jpeg"
    foto.write_bytes(b"imagen de prueba")  # una "foto" de mentira
    monkeypatch.setattr(telegram_service.requests, "post",
                        lambda *args, **kwargs: RespuestaFalsa())

    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", foto) is True


def test_foto_que_no_existe(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    no_existe = tmp_path / "no_existe.jpeg"
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", no_existe) is False


def test_foto_sin_internet(monkeypatch, tmp_path):
    poner_claves(monkeypatch)
    foto = tmp_path / "prueba.jpeg"
    foto.write_bytes(b"imagen de prueba")
    monkeypatch.setattr(telegram_service.requests, "post", internet_caido)
    assert telegram_service.enviar_foto_telegram("Mini Protud", "Movimiento", "Escuela", foto) is False
