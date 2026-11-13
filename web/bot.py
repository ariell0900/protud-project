# bot.py - Bot de Telegram de PROTUD
# Este archivo es el que "escucha" todo el tiempo.
# Cuando alguien le manda /start al bot, lo guarda en la base
# para que después le lleguen las alertas.
# Si alguien manda /stop, lo da de baja.
# Si alguien manda /alerta, manda una alerta de prueba a todos.

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                      # Leer variables del .env (el TOKEN del bot)
from pathlib import Path       # Armar rutas que funcionan en Windows y Linux
import psycopg                 # Conectar con PostgreSQL
import requests                # Hablar con la API de Telegram por internet
from dotenv import load_dotenv # Cargar el archivo .env con las claves

# Cargar las variables del .env que está en la misma carpeta
load_dotenv(Path(__file__).resolve().parent / ".env")

# TOKEN: la clave secreta del bot que nos dio @BotFather.
# Nunca se escribe acá, se lee del .env para no compartirla.
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# API: la dirección base para hablar con Telegram.
# Todos los mensajes pasan por acá.
API = f"https://api.telegram.org/bot{TOKEN}"

# ---------------------------------------------------------------
# Conexión a la base de datos
# ---------------------------------------------------------------
def conectar_db():
    """Devuelve una conexión abierta a PostgreSQL."""
    # En la nube (Render) usa DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg.connect(url, connect_timeout=5)
    # En tu compu usa los datos del .env
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5
    )

# ---------------------------------------------------------------
# Guardar suscriptor
# ---------------------------------------------------------------
def guardar_suscriptor(chat_id, nombre, username):
    """Guarda a una persona que puso /start, para mandarle alertas después."""
    # chat_id: es el número único que Telegram le da a cada chat.
    # Sin este número no le podemos mandar mensajes a nadie.
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("""
                INSERT INTO suscriptores_telegram (chat_id, nombre, username)
                VALUES (%s, %s, %s)
                -- Si esa persona ya estaba guardada, no la duplicamos,
                -- solo la volvemos a activar y actualizamos su nombre.
                ON CONFLICT (chat_id) DO UPDATE SET activo = TRUE, nombre = EXCLUDED.nombre
            """, (chat_id, nombre, username))

# ---------------------------------------------------------------
# Mandar un mensaje simple
# ---------------------------------------------------------------
def mandar(chat_id, texto):
    """Manda un mensaje de texto a un solo chat_id."""
    # sendMessage es el comando de Telegram para mandar texto.
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": texto},
        timeout=10
    )

# ---------------------------------------------------------------
# Escuchar mensajes (bucle principal)
# ---------------------------------------------------------------
def escuchar():
    """Queda esperando mensajes nuevos todo el tiempo."""
    # offset: le dice a Telegram "ya leí hasta este mensaje",
    # así no nos vuelve a mandar los mismos de nuevo.
    offset = 0
    print("Bot PROTUD escuchando... mandale /start en Telegram")

    # Bucle infinito: el bot nunca se apaga solo, siempre está atento.
    while True:
        # getUpdates: le preguntamos a Telegram "¿hay mensajes nuevos?"
        # timeout=30 significa que esperamos hasta 30 segundos la respuesta.
        r = requests.get(
            f"{API}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35
        ).json()

        # Recorremos cada mensaje nuevo que llegó.
        for update in r.get("result", []):
            # Avanzamos el offset para no leer este mensaje otra vez.
            offset = update["update_id"] + 1

            # Nos quedamos solo con los mensajes de texto.
            # Si no hay "message" (ej: es un sticker), lo saltamos.
            msg = update.get("message")
            if not msg:
                continue

            # Sacamos los datos de quien escribió.
            chat_id = msg["chat"]["id"]  # A quién hay que responderle
            texto = msg.get("text", "")  # Qué escribió (/start, /stop, etc.)
            nombre = msg["from"].get("first_name", "")
            username = msg["from"].get("username", "")

            # Si puso /start: lo guardamos y le avisamos que ya está suscripto.
            if texto == "/start":
                guardar_suscriptor(chat_id, nombre, username)
                mandar(chat_id, "✅ ¡Listo! Ya estás suscripto a las alertas de PROTUD.\nCuando el robot detecte algo, te llega acá.")

            # Si puso /stop: lo marcamos como inactivo, no le llegan más alertas.
            # No lo borramos (baja lógica), por si después quiere volver con /start.
            elif texto == "/stop":
                with conectar_db() as conexion:
                    with conexion.cursor() as cursor:
                        cursor.execute(
                            "UPDATE suscriptores_telegram SET activo = FALSE WHERE chat_id = %s",
                            (chat_id,)
                        )
                mandar(chat_id, "Te diste de baja de las alertas de PROTUD.")

            # Si puso /alerta: manda una alerta de prueba a TODOS los suscriptos.
            elif texto == "/alerta":
                from telegram_service import enviar_alerta_telegram
                enviar_alerta_telegram("Mini Protud", "Prueba de alerta", "Escuela")
                mandar(chat_id, "Prueba enviada a todos los suscriptos.")

# Si corremos este archivo directo (python bot.py), empieza a escuchar.
if __name__ == "__main__":
    escuchar()