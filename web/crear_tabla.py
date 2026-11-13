# crear_tabla.py - Se corre UNA sola vez.
# Crea la tabla "suscriptores_telegram" en PostgreSQL.
# Ahí se guardan todos los que le ponen /start al bot,
# para que después les lleguen las alertas.
# Después de correrlo, no hay que correrlo más.

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                      # Leer variables del .env
from pathlib import Path       # Armar rutas que funcionan en Windows y Linux
import psycopg                 # Conectar con PostgreSQL
from dotenv import load_dotenv # Cargar el archivo .env

# Cargar el .env que está en la misma carpeta
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------------
# Conectar a la base
# ---------------------------------------------------------------
# En la nube (Render) usa DATABASE_URL
url = os.getenv("DATABASE_URL")
if url:
    conn = psycopg.connect(url)
else:
    # En tu compu usa los datos del .env
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# ---------------------------------------------------------------
# Crear la tabla
# ---------------------------------------------------------------
# with conn: si algo falla, no guarda nada a medias.
with conn:
    with conn.cursor() as cur:
        cur.execute("""
            -- CREATE TABLE IF NOT EXISTS: si ya existe, no la vuelve a crear
            -- ni borra lo que ya hay adentro, no rompe nada.
            CREATE TABLE IF NOT EXISTS suscriptores_telegram (
                -- id: número automático para cada fila
                id SERIAL PRIMARY KEY,
                -- chat_id: número único de Telegram de cada persona.
                -- UNIQUE para que nadie quede guardado 2 veces.
                chat_id BIGINT UNIQUE NOT NULL,
                -- nombre: nombre que tiene en Telegram (ej: Ari)
                nombre TEXT,
                -- username: @usuario de Telegram, si tiene
                username TEXT,
                -- fecha_suscripcion: cuándo puso /start, se pone sola
                fecha_suscripcion TIMESTAMP DEFAULT NOW(),
                -- activo: TRUE = le llegan alertas, FALSE = se dio de baja con /stop
                activo BOOLEAN DEFAULT TRUE
            );
        """)

print("Tabla creada!")

# Cerramos la conexión
conn.close()