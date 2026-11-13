# telegram_service.py - Manda avisos por Telegram.
# Antes mandaba a UN solo chat_id del .env.
# Ahora busca a TODOS los suscriptos en la tabla
# "suscriptores_telegram" y les manda la alerta a cada uno.
# Por eso app.py no cambia: ya llamaba a estas 2 funciones,
# ahora esas funciones solas ya mandan a todos.

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                      # Leer variables del .env
from pathlib import Path       # Armar rutas que funcionan en Windows y Linux
import psycopg                 # Conectar con PostgreSQL
import requests                # Hablar con la API de Telegram
from dotenv import load_dotenv # Cargar el .env

# Cargar el .env
load_dotenv(Path(__file__).resolve().parent / ".env")

# TOKEN del bot, se lee del .env para no compartirlo
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

# ---------------------------------------------------------------
# Conexión a la base
# ---------------------------------------------------------------
def conectar_db():
    """Devuelve una conexión abierta a PostgreSQL."""
    # En Render usa DATABASE_URL
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
# Buscar a quién hay que avisarle
# ---------------------------------------------------------------
def obtener_suscriptores():
    """Devuelve la lista de chat_id de todos los que están suscriptos."""
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # Solo los activos: los que pusieron /start y no se dieron de baja con /stop
                cursor.execute("SELECT chat_id FROM suscriptores_telegram WHERE activo = TRUE")
                # fetchall trae filas como [(123,), (456,)] y con [fila[0] ...] nos quedamos solo con los números
                return [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        # Si la base falla, mostramos el error y devolvemos lista vacía
        # para que no se rompa toda la web.
        print("Error al buscar suscriptores:", e)
        return []

# ---------------------------------------------------------------
# Mandar alerta de texto
# ---------------------------------------------------------------
def enviar_alerta_telegram(robot, evento, ubicacion):
    """Manda una alerta de texto a TODOS los suscriptos. Devuelve True si al menos a uno le llegó."""
    # 1) Buscamos a quién hay que avisarle
    suscriptores = obtener_suscriptores()

    # Si nadie puso /start todavía, no hay a quién mandarle
    if not suscriptores:
        print("No hay suscriptores todavia")
        return False

    # 2) Armamos el mensaje que van a recibir
    mensaje = f"🚨 ALERTA PROTUD\nRobot: {robot}\nEvento: {evento}\nUbicacion: {ubicacion}"

    # 3) Lo mandamos uno por uno, con un bucle for
    ok = False  # Va a quedar True si a al menos uno le llegó
    for chat_id in suscriptores:
        # try/except: si a uno le falla (sin internet, bloqueó al bot, etc.)
        # no se corta el bucle, sigue con el siguiente y al final devuelve True/False
        try:
            # sendMessage: comando de Telegram para mandar texto
            r = requests.post(
                f"{API}/sendMessage",
                json={"chat_id": chat_id, "text": mensaje},
                timeout=10
            )
            # 200 significa que Telegram lo aceptó
            if r.status_code == 200:
                ok = True
        except Exception as e:
            # Mostramos el error pero no rompemos la web
            print("Error al enviar alerta:", e)
    return ok

# ---------------------------------------------------------------
# Mandar alerta con foto
# ---------------------------------------------------------------
def enviar_foto_telegram(robot, evento, ubicacion, ruta_foto):
    """Manda una foto con texto a TODOS los suscriptos. Devuelve True si al menos a uno le llegó."""
    # 1) Buscamos a quién hay que avisarle
    suscriptores = obtener_suscriptores()
    if not suscriptores:
        print("No hay suscriptores todavia")
        return False

    # 2) Armamos el texto que va abajo de la foto (caption)
    mensaje = f"🚨 ALERTA PROTUD\nRobot: {robot}\nEvento: {evento}\nUbicacion: {ubicacion}"

    # 3) Mandamos la foto uno por uno
    ok = False
    for chat_id in suscriptores:
        # try/except: si la foto no existe o se cae internet,
        # devuelve False en vez de romper todo con un error
        try:
            # Abrimos la foto en modo "leer binario" (rb) porque es una imagen
            with open(ruta_foto, "rb") as foto:
                # sendPhoto: comando de Telegram para mandar foto
                # data: el texto y a quién va, files: la foto
                r = requests.post(
                    f"{API}/sendPhoto",
                    data={"chat_id": chat_id, "caption": mensaje},
                    files={"photo": foto},
                    timeout=15
                )
                if r.status_code == 200:
                    ok = True
        except Exception as e:
            print("Error al enviar foto:", e)
    return ok