# telegram_service.py - Manda avisos por Telegram.
# ANTES:
#   Mandaba a UN solo chat_id del .env.
# DESPUÉS (tu versión actual):
#   Busca a TODOS los suscriptos en la tabla
#   "suscriptores_telegram" y les manda la alerta a cada uno.
# AHORA (Etapa 2B):
#   Si le pasás robot_id, manda SOLO a los suscriptos
#   que son miembros de ESE robot.
#   Si no le pasás robot_id, manda a todos como antes,
#   para no romper /probar-telegram.
#
# Por eso app.py casi no cambia: ya llamaba a estas 2 funciones,
# ahora esas funciones solas ya filtran por robot.

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                      # Leer variables del .env
from pathlib import Path       # Armar rutas que funcionan en Windows y Linux
import psycopg                 # Conectar con PostgreSQL
import requests                # Hablar con la API de Telegram
from dotenv import load_dotenv # Cargar el .env

# Cargar el .env
# .env está en la misma carpeta que este archivo
load_dotenv(Path(__file__).resolve().parent / ".env")

# TOKEN del bot, se lee del .env para no compartirlo
# Lo conseguís hablando con @BotFather en Telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

# ---------------------------------------------------------------
# Conexión a la base
# ---------------------------------------------------------------
def conectar_db():
    """Devuelve una conexión abierta a PostgreSQL."""
    # En Render usa DATABASE_URL
    # DATABASE_URL ya trae todo junto: usuario, contraseña, host, base
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
# Buscar a quién hay que avisarle - TODOS
# ---------------------------------------------------------------
def obtener_suscriptores():
    """
    Devuelve la lista de chat_id de todos los que están suscriptos.

    Ejemplo: ["123456789", "987654321"]

    Solo los activos: los que pusieron /start y no se dieron de baja con /stop
    """
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # activo = TRUE = sigue suscripto
                # activo = FALSE = puso /stop, no le mandamos más
                cursor.execute("SELECT chat_id FROM suscriptores_telegram WHERE activo = TRUE")
                # fetchall trae filas como [(123,), (456,)] y con [fila[0] ...] nos quedamos solo con los números
                return [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        # Si la base falla, mostramos el error y devolvemos lista vacía
        # para que no se rompa toda la web.
        print("Error al buscar suscriptores:", e)
        return []

# ---------------------------------------------------------------
# NUEVO - ETAPA 2B: Buscar solo los miembros de UN robot
# ---------------------------------------------------------------
def obtener_suscriptores_por_robot(robot_id):
    """
    Devuelve solo los chat_id de los suscriptos que son miembros de ESE robot.

    Ejemplo:
      Robot 1 tiene a Ariel y Emiliano.
      Robot 2 tiene a Sofía.
      Si robot_id = 1, devuelve solo [chat de Ariel, chat de Emiliano].
      A Sofía NO le llega la alerta del Robot 1.

    ¿Cómo lo sabe?
    Junta 3 tablas:
      1. suscriptores_telegram (quién tiene Telegram y cuál es su chat_id)
      2. usuarios (para saber si es admin)
      3. robot_usuarios (qué usuario puede ver qué robot)

    Regla:
      - Si sos administrador -> te llega TODO, de todos los robots.
        Porque el admin ve todos los robots en la web, entonces
        también le llegan todas las alertas.
      - Si sos operador -> te llega solo si estás en robot_usuarios
        para ese robot_id.

    ¿Qué pasa si tu tabla suscriptores_telegram todavía no tiene usuario_id?
    Abajo, en el PASO 1, tenés el SQL para agregarlo.
    Si todavía no lo agregaste, esta función devuelve a todos
    como antes, para no dejarte sin alertas.
    """
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:

                # ------------------------------------------------
                # ¿Tu tabla ya tiene usuario_id?
                # ------------------------------------------------
                # Miramos si existe la columna usuario_id en suscriptores_telegram.
                # Si no existe, no podemos filtrar por robot, así que
                # devolvemos a todos como antes.
                cursor.execute(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'suscriptores_telegram'
                      AND column_name = 'usuario_id'
                    """
                )
                tiene_usuario_id = cursor.fetchone() is not None

                if not tiene_usuario_id:
                    # Todavía no hiciste el PASO 1, mandamos a todos
                    print("suscriptores_telegram todavía no tiene usuario_id, mando a todos")
                    return obtener_suscriptores()

                # ------------------------------------------------
                # Ya tiene usuario_id, filtramos por robot
                # ------------------------------------------------
                # DISTINCT = si un usuario aparece 2 veces, lo mandamos 1 sola vez
                # JOIN usuarios = para saber el rol (admin / operador)
                # LEFT JOIN robot_usuarios = para saber si es miembro de ese robot
                # WHERE activo = TRUE = solo los que no pusieron /stop
                cursor.execute(
                    """
                    SELECT DISTINCT s.chat_id
                    FROM suscriptores_telegram AS s
                    JOIN usuarios AS u ON u.id = s.usuario_id
                    LEFT JOIN robot_usuarios AS ru
                        ON ru.usuario_id = s.usuario_id
                        AND ru.robot_id = %s
                    WHERE s.activo = TRUE
                      AND (
                        -- Admin: le llega todo
                        u.rol = 'administrador'
                        -- Operador: solo si está en robot_usuarios para ese robot
                        OR ru.usuario_id IS NOT NULL
                      )
                    """,
                    (robot_id,),
                )

                # Misma idea que antes: nos quedamos solo con los chat_id
                return [fila[0] for fila in cursor.fetchall()]

    except Exception as e:
        print("Error al buscar suscriptores por robot:", e)
        # Si algo falla, por seguridad mandamos a todos,
        # mejor que no le llegue a nadie una alerta importante
        return obtener_suscriptores()

# ---------------------------------------------------------------
# Mandar alerta de texto
# ---------------------------------------------------------------
def enviar_alerta_telegram(robot, evento, ubicacion, robot_id=None):
    """
    Manda una alerta de texto a los suscriptos.

    Parámetros:
      robot = nombre del robot, ej: "Mini Protud"
      evento = qué pasó, ej: "Movimiento detectado"
      ubicacion = dónde, ej: "Escuela"
      robot_id = NUEVO, opcional. Ej: 1

    ¿Qué hace con robot_id?
      - Si le pasás robot_id=1 -> manda SOLO a miembros del Robot 1 + admins.
      - Si no le pasás nada (robot_id=None) -> manda a TODOS como antes.
        Así /probar-telegram sigue andando sin cambiar nada.

    Devuelve True si al menos a uno le llegó.
    """
    # 1) Buscamos a quién hay que avisarle
    # Si me dijeron de qué robot es, filtro. Si no, a todos.
    if robot_id is not None:
        suscriptores = obtener_suscriptores_por_robot(robot_id)
    else:
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
def enviar_foto_telegram(robot, evento, ubicacion, ruta_foto, robot_id=None):
    """
    Manda una foto con texto a los suscriptos.

    Igual que enviar_alerta_telegram, pero con foto.
    robot_id = opcional, si lo pasás filtra por miembros de ese robot.

    Devuelve True si al menos a uno le llegó.
    """
    # 1) Buscamos a quién hay que avisarle
    # Misma lógica: si hay robot_id, filtramos. Si no, a todos.
    if robot_id is not None:
        suscriptores = obtener_suscriptores_por_robot(robot_id)
    else:
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

# ---------------------------------------------------------------
# NUEVO - Ayuda para vincular Telegram con un usuario
# ---------------------------------------------------------------
def vincular_suscriptor(chat_id, usuario_id, username=None):
    """
    Vincula un chat_id de Telegram con un usuario de la web.

    ¿Cuándo se usa?
    Cuando el usuario manda /vincular PROTUD-TG-XXXX al bot,
    o cuando vos, desde app.py, querés decir:
    "este chat_id es de Ariel".

    Guarda o actualiza la fila en suscriptores_telegram:
      - Si ya existía ese chat_id, le pone el usuario_id
      - Si no existía, crea la fila nueva

    Esto es lo que hace que después obtener_suscriptores_por_robot()
    pueda filtrar, porque ya sabe qué chat es de qué usuario.
    """
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO suscriptores_telegram (chat_id, usuario_id, username, activo)
                    VALUES (%s, %s, %s, TRUE)
                    ON CONFLICT (chat_id)
                    DO UPDATE SET
                        usuario_id = EXCLUDED.usuario_id,
                        username = EXCLUDED.username,
                        activo = TRUE
                    """,
                    (str(chat_id), usuario_id, username),
                )
        return True
    except Exception as e:
        print("Error al vincular suscriptor:", e)
        return False