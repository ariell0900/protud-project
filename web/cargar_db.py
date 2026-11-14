# cargar_db.py - Se puede correr las veces que haga falta.
# Crea todas las tablas de Protud en la base de datos nueva de Render.
# Si una tabla ya existe, no la vuelve a crear ni borra nada.

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                  # Leer la variable DATABASE_URL
import psycopg             # Conectar con PostgreSQL
from pathlib import Path   # Armar rutas que funcionan en Windows y Linux

# ---------------------------------------------------------------
# Conectar a la base
# ---------------------------------------------------------------
# Carpeta donde están los archivos .sql (web/db)
carpeta = Path(__file__).resolve().parent / "db"

# Nos conectamos con la URL de la base (la External de Render)
conn = psycopg.connect(os.environ["DATABASE_URL"])


# ---------------------------------------------------------------
# Función: ver si una tabla ya existe
# ---------------------------------------------------------------
def tabla_existe(nombre):
    """Devuelve True si la tabla ya está creada en la base."""
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{nombre}",))
        return cur.fetchone()[0] is not None


# ---------------------------------------------------------------
# Función: correr un archivo .sql
# ---------------------------------------------------------------
def correr_sql(archivo):
    """Lee un archivo .sql de la carpeta db y lo ejecuta en la base."""
    # Leemos el archivo línea por línea
    lineas = (carpeta / archivo).read_text(encoding="utf-8").splitlines()

    # Sacamos las líneas que empiezan con "\" porque son comandos
    # de psql (otro programa) y psycopg no las entiende
    sql = "\n".join(l for l in lineas if not l.startswith("\\"))

    with conn.cursor() as cur:
        # Aseguramos que las tablas se creen en el esquema "public"
        cur.execute("SET search_path TO public;")
        # Ejecutamos todo el SQL del archivo
        cur.execute(sql)
        # schema_actual.sql deja el esquema vacío al terminar,
        # así que lo volvemos a poner en "public" para lo que sigue
        cur.execute("SET search_path TO public;")

    # Guardamos los cambios
    conn.commit()
    print("OK:", archivo)


# ---------------------------------------------------------------
# Crear las tablas
# ---------------------------------------------------------------
# 1) usuarios, robots, alertas, imagenes y notificaciones
#    Solo se corre si todavía no existe la tabla "usuarios",
#    porque este archivo no trae IF NOT EXISTS y daría error.
if tabla_existe("usuarios"):
    print("SALTADO: schema_actual.sql (las tablas ya existen)")
else:
    correr_sql("schema_actual.sql")

# 2) mensajes del chat (necesita que ya existan robots y usuarios)
correr_sql("chat.sql")

# 3) suscriptores_telegram (la misma tabla de crear_tabla.py)
with conn.cursor() as cur:
    cur.execute("""
        -- IF NOT EXISTS: si ya existe, no la vuelve a crear
        CREATE TABLE IF NOT EXISTS public.suscriptores_telegram (
            id SERIAL PRIMARY KEY,                    -- número automático
            chat_id BIGINT UNIQUE NOT NULL,           -- id de Telegram (no se repite)
            nombre TEXT,                              -- nombre en Telegram
            username TEXT,                            -- @usuario, si tiene
            fecha_suscripcion TIMESTAMP DEFAULT NOW(),-- cuándo puso /start
            activo BOOLEAN DEFAULT TRUE               -- TRUE = le llegan alertas
        );
    """)
conn.commit()
print("OK: suscriptores_telegram")

# Cerramos la conexión
conn.close()