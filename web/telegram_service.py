import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def enviar_alerta_telegram(robot, evento, ubicacion):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("ERROR: Faltan datos de Telegram.")
        return False

    mensaje = (
        "🚨 ALERTA DE SEGURIDAD - PROTUD\n\n"
        f"🤖 Robot: {robot}\n"
        f"📍 Ubicación: {ubicacion}\n"
        f"⚠️ Evento: {evento}\n\n"
        "Sistema de Vigilancia Robótica PROTUD"
    )

    try:
        respuesta = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": mensaje
            },
            timeout=10
        )

        respuesta.raise_for_status()

        return respuesta.json().get("ok", False)

    except requests.RequestException as error:
        print(
            "Error al enviar la alerta:",
            type(error).__name__
        )
        return False


# NUEVO: manda la alerta con una foto
def enviar_foto_telegram(robot, evento, ubicacion, ruta_foto):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("ERROR: Faltan datos de Telegram.")
        return False

    texto = (
        "🚨 ALERTA DE SEGURIDAD - PROTUD\n\n"
        f"🤖 Robot: {robot}\n"
        f"📍 Ubicación: {ubicacion}\n"
        f"⚠️ Evento: {evento}\n\n"
        "Sistema de Vigilancia Robótica PROTUD"
    )

    try:
        with open(ruta_foto, "rb") as foto:
            respuesta = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": texto
                },
                files={"photo": foto},
                timeout=20
            )

        respuesta.raise_for_status()

        return respuesta.json().get("ok", False)

    except (requests.RequestException, OSError) as error:
        print(
            "Error al enviar la foto:",
            type(error).__name__
        )
        return False