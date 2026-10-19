
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN")

if not token:
    print("ERROR: No se encontró TELEGRAM_BOT_TOKEN en .env")
else:
    try:
        respuesta = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            timeout=10
        )
        respuesta.raise_for_status()
        datos = respuesta.json()

        if not datos.get("ok"):
            print("Telegram rechazó la solicitud.")
        elif not datos.get("result"):
            print("No hay mensajes. Enviá /start al bot nuevamente.")
        else:
            for evento in datos["result"]:
                mensaje = evento.get("message", {})
                chat = mensaje.get("chat", {})

                if chat.get("id"):
                    print("Chat ID:", chat["id"])

    except requests.RequestException:
        print("No se pudo consultar Telegram. Revisá la conexión y el token.")
