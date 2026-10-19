
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Cargar la configuración privada
load_dotenv(Path(__file__).resolve().parent / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not token or not chat_id:
    print("ERROR: Faltan datos de Telegram en .env")
else:
    mensaje = (
        "🚨 ALERTA DE SEGURIDAD - PROTUD\n\n"
        "🤖 Robot: Mini Protud\n"
        "📍 Ubicación: Escuela\n"
        "⚠️ Evento: Movimiento detectado (SIMULACIÓN)\n"
        "🔔 Estado: Notificación de prueba\n\n"
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
        datos = respuesta.json()

        if datos.get("ok"):
            print("¡Alerta enviada correctamente a Telegram!")
        else:
            print("Telegram no pudo enviar la alerta.")


    except requests.RequestException as error:
        print("Error al conectar con Telegram.")
        print("Tipo de error:", type(error).__name__)

        if error.response is not None:
            print("Código HTTP:", error.response.status_code)
            print("Detalle:", error.response.json().get("description", "Sin descripción"))