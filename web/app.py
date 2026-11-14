"""
PROTUD - Aplicación web (Flask)

Aplicación web del robot de vigilancia Protud.

FUNCIONES PRINCIPALES:
- Login con Google.
- Panel de control.
- Alertas.
- Fotos.
- Notificaciones de Telegram.
- Administración de usuarios.
- Sistema de chat por robot (en vivo, cada 2 segundos).
- Mis Robots + códigos de invitación (Etapa 2).

SEGURIDAD:
- Las páginas privadas requieren iniciar sesión.
- Las páginas administrativas requieren rol "administrador".
- El chat comprueba que el usuario tenga permiso sobre el robot.
- No se confía únicamente en el parámetro ?robot=...
"""

# ===============================================================
# LIBRERÍAS
# ===============================================================
# Librerías = herramientas que importamos para usar después.
# Si falta alguna, el programa no arranca.

import os
# os = para leer variables de entorno (SECRET_KEY, DATABASE_URL, etc.)
# Las variables de entorno son datos secretos que están en .env,
# no escritos en el código.

from pathlib import Path
# Path = para armar rutas de archivos (ej: dónde está el .env)

from functools import wraps
# wraps = para que los decoradores @login_required no rompan
# el nombre de la función original.

import psycopg
# psycopg = librería para hablar con PostgreSQL (la base de datos)

# ---------------------------------------------------------------
# NUEVO - ETAPA 2: para los códigos de invitación
# ---------------------------------------------------------------
import secrets
# secrets = para generar códigos aleatorios seguros.
# No usamos random porque secrets es más difícil de adivinar.

import string
# string = tiene las letras y números. Acá no lo usamos directo
# pero lo dejamos por si querés cambiar el alfabeto del código.

from datetime import datetime, timedelta
# datetime = para saber la fecha/hora actual (ej: ahora)
# timedelta = para sumar tiempo (ej: ahora + 24 horas = cuándo vence el código)

from dotenv import load_dotenv
# load_dotenv = lee el archivo .env y carga las variables

from flask import (
    Flask,           # Flask = para crear la aplicación web
    render_template, # render_template = para mostrar un .html
    redirect,        # redirect = para mandar a otra página (ej: después de borrar)
    url_for,         # url_for = busca la URL de una función (ej: url_for('panel') -> /panel)
    session,         # session = cajita donde guardamos quién está logueado
    request,         # request = lo que manda el navegador (form, ?robot=1, JSON)
    jsonify,         # jsonify = para devolver JSON en la API del chat
)

from werkzeug.middleware.proxy_fix import ProxyFix
# ProxyFix = para que Flask entienda que está detrás de Render / proxy

from authlib.integrations.flask_client import OAuth
# OAuth = para el login con Google

from telegram_service import (
    enviar_alerta_telegram,
    enviar_foto_telegram,
)
# telegram_service = archivo nuestro que manda mensajes a Telegram

# ---------------------------------------------------------------
# NUEVO - BOT POR WEBHOOK (OPCIÓN 1 GRATIS)
# ---------------------------------------------------------------
# Antes el bot corría aparte con bot.py y polling.
# Eso en Render es pago (Background Worker).
# Ahora el bot vive adentro de esta misma página.
# Telegram le manda los mensajes a /webhook y acá los atendemos.
# Así no pagamos nada extra y anda aunque tu compu esté apagada.
import requests
# requests = para mandar mensajes de vuelta a Telegram
# (ej: responder "¡Listo! Ya estás suscripto")

# ===============================================================
# CONFIGURACIÓN INICIAL
# ===============================================================

# Cargar el .env que está junto a app.py
# .env tiene: SECRET_KEY, GOOGLE_CLIENT_ID, DATABASE_URL, etc.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Crear aplicación Flask
# app es la aplicación web. Todas las rutas cuelgan de acá.
app = Flask(__name__)

# ---------------------------------------------------------------
# ProxyFix
# ---------------------------------------------------------------
# Necesario cuando la aplicación está detrás de un proxy,
# como puede ocurrir en Render.
#
# Esto permite que Flask reconozca correctamente HTTPS y el host.
# ---------------------------------------------------------------
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_proto=1,
    x_host=1,
)

# ===============================================================
# CONFIGURACIÓN DE SESIÓN
# ===============================================================

# SECRET_KEY = clave secreta para firmar las cookies de sesión.
# Si alguien la conoce, puede falsificar sesiones.
SECRET_KEY = os.getenv("SECRET_KEY")

# Si no tenemos SECRET_KEY, es mejor detener la aplicación.
# Sin esta clave, las sesiones de Flask no están correctamente
# protegidas.
if not SECRET_KEY:
    raise RuntimeError(
        "Falta SECRET_KEY en el archivo .env"
    )

app.secret_key = SECRET_KEY

# ---------------------------------------------------------------
# Cookies de sesión
# ---------------------------------------------------------------

# JavaScript del navegador no puede leer la cookie de sesión.
# Así, si hay un script malo, no te roba la sesión.
app.config["SESSION_COOKIE_HTTPONLY"] = True

# Evita que la cookie se envíe en la mayoría de peticiones
# cross-site (de otra página).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# En producción HTTPS debe estar activo.
#
# Si estás trabajando en http://127.0.0.1:5000 lo dejamos
# desactivado para que puedas probar localmente.
#
# En Render deberías poner:
#
# SESSION_COOKIE_SECURE=true
#
# en las variables de entorno.
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)

# ===============================================================
# GOOGLE OAUTH
# ===============================================================
# OAuth = sistema para loguearse con Google sin que nosotros
# guardemos la contraseña del usuario.
# Google nos dice: "sí, es Ariel, su email es..."

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
        # scope = qué datos pedimos: id, email y perfil (nombre)
    },
)

# ===============================================================
# CONEXIÓN A POSTGRESQL
# ===============================================================

def conectar_db():
    """
    Devuelve una conexión a PostgreSQL.

    En Render:
        usa DATABASE_URL

    En la computadora:
        usa DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD
        definidos en .env.
    """

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # En Render, DATABASE_URL ya trae todo junto
        return psycopg.connect(
            database_url,
            connect_timeout=5  # Si en 5 seg no conecta, da error
        )

    # En local, armamos la conexión con los datos sueltos
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )

# ===============================================================
# FUNCIONES DE SEGURIDAD
# ===============================================================

def login_required(func):
    """
    Decorador que protege una ruta.

    Si el usuario NO inició sesión:
        lo manda a Google Login.

    Si ya inició sesión:
        permite continuar.

    Ejemplo:
        @app.route("/panel")
        @login_required
        def panel(): ...
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        # session.get("usuario") = ¿hay alguien logueado?
        usuario = session.get("usuario")

        if not usuario:
            return redirect(url_for("login_google"))

        return func(*args, **kwargs)

    return wrapper

def admin_required(func):
    """
    Decorador para rutas exclusivas del administrador.

    Primero comprueba que haya sesión.
    Después comprueba que el rol sea:
        administrador

    Si es operador, le muestra 403 (prohibido).
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        usuario = session.get("usuario")

        # No está logueado
        if not usuario:
            return redirect(url_for("login_google"))

        # Está logueado pero no es administrador
        if usuario.get("rol") != "administrador":
            return "No tenés permiso.", 403

        return func(*args, **kwargs)

    return wrapper

def usuario_puede_ver_robot(usuario_id, rol, robot_id):
    """
    Comprueba si un usuario puede acceder al chat de un robot.

    IMPORTANTE:

    Para solucionar el problema de seguridad de:

        /chat?robot=1
        /chat?robot=2
        /chat?robot=3

    necesitamos relacionar usuarios con robots.

    La tabla utilizada es:

        robot_usuarios

    con:

        robot_id
        usuario_id

    El administrador puede acceder a todos los robots.

    Un operador solamente puede acceder a los robots que tenga
    asignados.

    Si la tabla todavía no existe, un operador NO obtiene acceso.
    Esto es intencional: es mucho más seguro bloquear el acceso
    que mostrar accidentalmente chats de otros equipos.
    """

    # Administrador = acceso total
    if rol == "administrador":
        return True

    try:
        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # Buscamos si existe la fila (robot_id, usuario_id)
                # LIMIT 1 = basta con encontrar 1, no hace falta contar todas
                cursor.execute(
                    """
                    SELECT 1
                    FROM robot_usuarios
                    WHERE robot_id = %s
                      AND usuario_id = %s
                    LIMIT 1
                    """,
                    (robot_id, usuario_id),
                )

                # Si fetchone() da algo, existe -> True. Si da None -> False
                return cursor.fetchone() is not None

    except psycopg.Error:

        # Si la comprobación de permisos falla,
        # por seguridad NO damos acceso.
        app.logger.exception(
            "Error comprobando permisos del robot"
        )

        return False

# ===============================================================
# PÁGINA PRINCIPAL
# ===============================================================

@app.route("/")
def inicio():
    """
    Página pública principal.

    Mostrar la portada no necesita login.
    """

    return render_template("index.html")

# ===============================================================
# PANEL
# ===============================================================

@app.route("/panel")
@login_required
def panel():
    """
    Panel principal.

    SOLO usuarios logueados.
    Muestra: alertas pendientes, alertas últimas 24h,
    cantidad de fotos y las últimas 5 alertas.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # COUNT(*) FILTER = cuenta solo las filas que cumplen la condición
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (
                            WHERE NOT atendida
                        ),
                        COUNT(*) FILTER (
                            WHERE fecha_hora >=
                            NOW() - INTERVAL '24 hours'
                        ),
                        COUNT(foto_url)
                    FROM alertas
                    """
                )

                (
                    pendientes,
                    ultimas_24h,
                    imagenes,
                ) = cursor.fetchone()

                # Últimas 5 alertas, de la más nueva a la más vieja
                cursor.execute(
                    """
                    SELECT
                        fecha_hora,
                        tipo,
                        atendida
                    FROM alertas
                    ORDER BY fecha_hora DESC
                    LIMIT 5
                    """
                )

                ultimas = cursor.fetchall()

        return render_template(
            "panel.html",
            pendientes=pendientes,
            ultimas_24h=ultimas_24h,
            imagenes=imagenes,
            ultimas=ultimas,
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al cargar el panel"
        )

        return (
            "No se pudo cargar el panel.",
            500,
        )

# ===============================================================
# ROBOT
# ===============================================================

@app.route("/robot")
@login_required
def robot():
    """
    Página que muestra la última alerta del robot.

    También queda protegida porque contiene información
    del sistema.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # LIMIT 1 = solo la última alerta
                cursor.execute(
                    """
                    SELECT
                        tipo,
                        descripcion,
                        fecha_hora,
                        atendida
                    FROM alertas
                    ORDER BY fecha_hora DESC
                    LIMIT 1
                    """
                )

                ultima = cursor.fetchone()

        return render_template(
            "robot.html",
            ultima=ultima,
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al cargar el robot"
        )

        return (
            "No se pudo cargar la página del robot.",
            500,
        )

# ===============================================================
# CONTROL
# ===============================================================

@app.route("/control")
@login_required
def control():
    """
    Página de control del robot.

    Queda protegida porque podría contener controles
    que no deben estar disponibles públicamente.
    """

    return render_template("control.html")

# ===============================================================
# FOTOS
# ===============================================================

@app.route("/fotos")
@login_required
def fotos():
    """
    Fotos del robot.

    IMPORTANTE:
    Actualmente las fotos son de ejemplo.
    """

    lista = [
        {
            "archivo": "robot.jpg",
            "motivo": "Movimiento detectado",
            "fecha": "18/10/2026 03:15",
        },
        {
            "archivo": "robot.jpg",
            "motivo": "Obstáculo en el pasillo",
            "fecha": "17/10/2026 22:40",
        },
        {
            "archivo": "robot.jpg",
            "motivo": "Patrulla de prueba",
            "fecha": "17/10/2026 20:05",
        },
    ]

    return render_template(
        "fotos.html",
        fotos=lista,
    )

# ===============================================================
# PRUEBA DE BASE DE DATOS
# ===============================================================

@app.route("/probar-db")
@admin_required
def probar_db():
    """
    Ruta de diagnóstico.

    Solo administrador.

    No conviene dejar endpoints de diagnóstico públicos.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    "SELECT COUNT(*) FROM robots"
                )

                cantidad = cursor.fetchone()[0]

        return (
            "PROTUD conectado a PostgreSQL. "
            f"Robots registrados: {cantidad}"
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al conectar con PostgreSQL"
        )

        return (
            "No se pudo conectar con PostgreSQL. "
            "Revisá la terminal.",
            500,
        )

# ===============================================================
# ALERTAS
# ===============================================================

@app.route("/alertas")
@login_required
def ver_alertas():
    """
    Muestra todas las alertas.

    Antes esta ruta podía abrirse directamente sin login.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # JOIN = juntamos alertas + robots para saber el nombre del robot
                cursor.execute(
                    """
                    SELECT
                        a.id,
                        r.nombre,
                        a.tipo,
                        a.descripcion,
                        a.fecha_hora,
                        a.atendida
                    FROM alertas AS a
                    JOIN robots AS r
                        ON a.robot_id = r.id
                    ORDER BY a.fecha_hora DESC
                    """
                )

                alertas = cursor.fetchall()

        return render_template(
            "alertas.html",
            alertas=alertas,
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al consultar alertas"
        )

        return (
            "No se pudieron consultar las alertas.",
            500,
        )

# ===============================================================
# ATENDER ALERTA
# ===============================================================

@app.route(
    "/alertas/<int:alerta_id>/atender",
    methods=["POST"],
)
@login_required
def atender_alerta(alerta_id):
    """
    Marca una alerta como atendida.

    Solamente se acepta POST.
    Así no se puede atender una alerta solo pegando una URL.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE alertas
                    SET atendida = TRUE
                    WHERE id = %s
                    """,
                    (alerta_id,),
                )

        return redirect(
            url_for("ver_alertas")
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al actualizar la alerta"
        )

        return (
            "No se pudo actualizar la alerta.",
            500,
        )

# ===============================================================
# DESHACER ALERTA
# ===============================================================

@app.route(
    "/alertas/<int:alerta_id>/deshacer",
    methods=["POST"],
)
@login_required
def deshacer_alerta(alerta_id):
    """
    Vuelve una alerta a estado pendiente.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE alertas
                    SET atendida = FALSE
                    WHERE id = %s
                    """,
                    (alerta_id,),
                )

        return redirect(
            url_for("ver_alertas")
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al deshacer la alerta"
        )

        return (
            "No se pudo deshacer la alerta.",
            500,
        )

# ===============================================================
# NOTIFICACIONES
# ===============================================================

@app.route("/notificaciones")
@login_required
def ver_notificaciones():
    """
    Lista las notificaciones enviadas por Telegram.

    Antes podía consultarse sin autenticación.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        n.id,
                        n.mensaje,
                        n.fecha_envio,
                        n.leida,
                        n.alerta_id,
                        n.estado_envio
                    FROM notificaciones AS n
                    ORDER BY n.fecha_envio DESC
                    """
                )

                notificaciones = cursor.fetchall()

        return render_template(
            "notificaciones.html",
            notificaciones=notificaciones,
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al consultar notificaciones"
        )

        return (
            "No se pudieron consultar las notificaciones.",
            500,
        )

# ===============================================================
# PRUEBA TELEGRAM
# ===============================================================

@app.route("/probar-telegram")
@admin_required
def probar_telegram_flask():
    """
    Prueba manual de Telegram.

    Solo administrador.
    """

    enviado = enviar_alerta_telegram(
        robot="Mini Protud",
        evento="Movimiento detectado (SIMULACIÓN)",
        ubicacion="Escuela",
    )

    if enviado:
        return (
            "PROTUD: Notificación enviada "
            "correctamente a Telegram."
        )

    return (
        "PROTUD: No se pudo enviar "
        "la notificación.",
        500,
    )

# ===============================================================
# REGISTRAR NOTIFICACIÓN
# ===============================================================

def registrar_notificacion(
    alerta_id,
    mensaje,
    enviado,
):
    """
    Guarda en PostgreSQL el resultado del envío
    de una notificación.

    Si enviado = True -> estado = "enviada"
    Si enviado = False -> estado = "fallida"
    """

    estado = (
        "enviada"
        if enviado
        else "fallida"
    )

    with conectar_db() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO notificaciones
                    (
                        alerta_id,
                        mensaje,
                        estado_envio
                    )
                VALUES
                    (%s, %s, %s)
                RETURNING id
                """,
                (
                    alerta_id,
                    mensaje,
                    estado,
                ),
            )

            # RETURNING id = la base nos devuelve el id que le puso
            return cursor.fetchone()[0]

# ===============================================================
# SIMULAR ALERTA
# ===============================================================

@app.route(
    "/simular-alerta",
    methods=["POST"],
)
@admin_required
def simular_alerta():
    """
    Crea una alerta de prueba.

    Solo administrador.

    Esto evita que cualquier persona pueda
    generar alertas falsas desde Internet.
    """

    try:

        # -------------------------------------------------------
        # 1. Crear alerta en PostgreSQL
        # -------------------------------------------------------

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO alertas
                        (
                            robot_id,
                            tipo,
                            descripcion
                        )
                    VALUES
                        (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        1,  # robot_id = 1 (Mini Protud)
                        "movimiento",
                        "Mini Protud detectó movimiento "
                        "(SIMULACIÓN)",
                    ),
                )

                alerta_id = cursor.fetchone()[0]

        # -------------------------------------------------------
        # 2. Mandar foto de prueba a Telegram
        # -------------------------------------------------------

        enviado = enviar_foto_telegram(
            robot="Mini Protud",
            evento="Movimiento detectado (SIMULACIÓN)",
            ubicacion="Escuela",
            ruta_foto=(
                Path(__file__).resolve().parent
                / "static"
                / "prueba.jpeg"
            ),
        )

        # -------------------------------------------------------
        # 3. Registrar resultado
        # -------------------------------------------------------

        mensaje = (
            "Mini Protud detectó movimiento "
            "(SIMULACIÓN)"
        )

        notificacion_id = registrar_notificacion(
            alerta_id,
            mensaje,
            enviado,
        )

        # 201 = creado correctamente
        return {
            "alerta_id": alerta_id,
            "notificacion_id": notificacion_id,
            "registrada": True,
            "telegram_enviado": enviado,
        }, 201

    except psycopg.Error:

        app.logger.exception(
            "Error al registrar la alerta"
        )

        return {
            "error": (
                "No se pudo registrar la alerta"
            )
        }, 500

# ===============================================================
# LOGIN CON GOOGLE
# ===============================================================

@app.route("/login/google")
def login_google():
    """
    Envía al usuario a Google para autenticarse.
    """

    return google.authorize_redirect(
        url_for(
            "callback",
            _external=True,  # URL completa, porque Google tiene que volver
        )
    )

# ===============================================================
# CALLBACK DE GOOGLE
# ===============================================================

@app.route("/callback")
def callback():
    """
    Google vuelve aquí después del login.

    Acá:
    1. verificamos el token,
    2. obtenemos nombre/email,
    3. buscamos o creamos al usuario,
    4. comprobamos si está activo,
    5. creamos la sesión Flask.
    """

    try:

        # Obtener y validar token
        token = google.authorize_access_token()

        # userinfo = datos que nos da Google: nombre, email, foto
        datos = token["userinfo"]

    except Exception:

        app.logger.exception(
            "Error durante el login con Google"
        )

        return (
            "No se pudo completar el inicio de sesión.",
            401,
        )

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # Crear usuario si no existe.
                #
                # Los usuarios nuevos comienzan como operador.
                # ON CONFLICT (email) = si el email ya existe,
                # no crea otro, solo actualiza el nombre.
                cursor.execute(
                    """
                    INSERT INTO usuarios
                        (
                            nombre,
                            email,
                            rol
                        )
                    VALUES
                        (
                            %s,
                            %s,
                            'operador'
                        )
                    ON CONFLICT (email)
                    DO UPDATE SET
                        nombre = EXCLUDED.nombre
                    RETURNING
                        id,
                        rol,
                        activo
                    """,
                    (
                        datos["name"],
                        datos["email"],
                    ),
                )

                (
                    usuario_id,
                    rol,
                    activo,
                ) = cursor.fetchone()

    except psycopg.Error:

        app.logger.exception(
            "Error al guardar el usuario"
        )

        return (
            "No se pudo iniciar sesión.",
            500,
        )

    # -----------------------------------------------------------
    # Baja lógica
    # -----------------------------------------------------------
    # Si activo = False, no puede entrar aunque tenga Google válido.
    if not activo:

        # Limpiamos cualquier sesión anterior
        session.clear()

        return (
            "Tu cuenta está dada de baja.",
            403,
        )

    # -----------------------------------------------------------
    # Crear sesión
    # -----------------------------------------------------------
    # Guardamos en session quién es, para no preguntar a la base
    # en cada página.

    session.clear()

    session["usuario"] = {
        "id": usuario_id,
        "nombre": datos["name"],
        "email": datos["email"],
        "rol": rol,
    }

    # Hacer la sesión permanente durante el tiempo configurado
    # por Flask.
    session.permanent = True

    return redirect(
        url_for("panel")
    )

# ===============================================================
# USUARIOS
# ===============================================================

@app.route("/usuarios")
@admin_required
def usuarios():
    """
    Lista de usuarios.

    SOLO administrador.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        nombre,
                        email,
                        rol,
                        activo
                    FROM usuarios
                    ORDER BY id
                    """
                )

                lista = cursor.fetchall()

        # NUEVO - ETAPA 2: mandamos también "usuario"
        # ¿Para qué? Para que usuarios.html sepa quién soy yo
        # y me muestre el cartelito "vos" y me oculte mis botones.
        # Antes solo mandaba "usuarios".
        return render_template(
            "usuarios.html",
            usuarios=lista,
            usuario=session.get("usuario"),
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al consultar usuarios"
        )

        return (
            "No se pudieron consultar los usuarios.",
            500,
        )

# ===============================================================
# BAJA DE USUARIO
# ===============================================================

@app.route(
    "/usuarios/<int:id>/baja",
    methods=["POST"],
)
@admin_required
def baja_usuario(id):
    """
    Da de baja lógicamente a un usuario.

    Baja lógica = NO borramos la fila.
    Solo ponemos activo = FALSE.

    Así el usuario no puede entrar más, pero:
    - sus mensajes del chat siguen guardados
    - sus alertas atendidas no se pierden
    - después se puede reactivar con 1 clic
    """

    # -----------------------------------------------------------
    # Protección: no me puedo dar de baja a mí mismo
    # -----------------------------------------------------------
    # ¿Por qué?
    # Si sos el único admin y te das de baja, te quedás afuera
    # y nadie más puede reactivarte desde la web.
    # session["usuario"]["id"] = el que está logueado ahora.
    # id = el usuario que quiere dar de baja.
    # Si son iguales, es a sí mismo -> lo frenamos.
    if id == session["usuario"]["id"]:
        return redirect(url_for("usuarios"))

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE usuarios
                    SET activo = FALSE
                    WHERE id = %s
                    """,
                    (id,),
                )

        return redirect(
            url_for("usuarios")
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al dar de baja al usuario"
        )

        return (
            "No se pudo dar de baja al usuario.",
            500,
        )

# ===============================================================
# REACTIVAR USUARIO
# ===============================================================

@app.route(
    "/usuarios/<int:id>/reactivar",
    methods=["POST"],
)
@admin_required
def reactivar_usuario(id):
    """
    Reactiva un usuario.
    Pone activo = TRUE de nuevo.
    """

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE usuarios
                    SET activo = TRUE
                    WHERE id = %s
                    """,
                    (id,),
                )

        return redirect(
            url_for("usuarios")
        )

    except psycopg.Error:

        app.logger.exception(
            "Error al reactivar al usuario"
        )

        return (
            "No se pudo reactivar al usuario.",
            500,
        )

# ===============================================================
# CAMBIAR ROL
# ===============================================================

@app.route(
    "/usuarios/<int:id>/rol",
    methods=["POST"],
)
@admin_required
def cambiar_rol(id):
    """
    Cambia el rol de un usuario entre:
        - administrador
        - operador

    ¿Para qué sirve?
    Ejemplo: Emiliano entró como operador, pero ahora también
    tiene que poder dar de baja usuarios. En vez de tocar la base
    a mano, el admin aprieta un botón en /usuarios y listo.

    ¿Cómo llega el rol nuevo?
    En usuarios.html hay un <form> con un <input hidden name="rol">
    que manda "administrador" o "operador".
    """

    # El rol nuevo viene del formulario
    rol_nuevo = request.form.get("rol")

    # -----------------------------------------------------------
    # 1. Validamos que el rol sea uno de los dos permitidos
    # -----------------------------------------------------------
    # Si alguien intenta mandar "dios" o "superadmin" desde el
    # inspector del navegador, lo frenamos acá.
    if rol_nuevo not in ("administrador", "operador"):
        return "Rol inválido.", 400

    # -----------------------------------------------------------
    # 2. Protección: no me puedo cambiar el rol a mí mismo
    # -----------------------------------------------------------
    # Si sos admin y te pasás a operador, perdés el acceso a /usuarios
    # y no te podés volver a hacer admin solo.
    if id == session["usuario"]["id"]:
        return redirect(url_for("usuarios"))

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # Actualizamos solo la columna rol
                cursor.execute(
                    """
                    UPDATE usuarios
                    SET rol = %s
                    WHERE id = %s
                    """,
                    (rol_nuevo, id),
                )

        # Volvemos a la tabla
        return redirect(url_for("usuarios"))

    except psycopg.Error:

        app.logger.exception(
            "Error al cambiar el rol"
        )

        return (
            "No se pudo cambiar el rol.",
            500,
        )

# ===============================================================
# ===============================================================
# ETAPA 2: MIS ROBOTS + CÓDIGOS DE INVITACIÓN
# ===============================================================
# ===============================================================
# ¿Para qué es esto?
# Antes, para que alguien vea un robot, vos tenías que agregarlo
# a mano en la tabla robot_usuarios con SQL.
#
# Ahora el dueño del robot genera un código tipo PROTUD-K7Q2
# y la otra persona se une sola pegando ese código.
#
# Flujo completo:
#   1. Admin crea código -> se guarda en tabla invitaciones
#   2. Operador pega código en /mis-robots -> si es válido,
#      se crea fila en robot_usuarios
#   3. A partir de ahí, usuario_puede_ver_robot() ya le da acceso
#      al chat, porque busca en robot_usuarios.
#
# Tablas que usa:
#   invitaciones  -> guarda los códigos
#   robot_usuarios -> guarda quién puede ver qué robot
# ===============================================================

def generar_codigo_invitacion():
    """
    Genera un código tipo PROTUD-K7Q2.

    - PROTUD- = prefijo fijo, para que se entienda que es de Protud
    - K7Q2 = 4 caracteres aleatorios, sin letras confusas
      (sin O, 0, I, 1) para que no se confunda al dictarlo por WhatsApp.

    Ejemplo: PROTUD-K7Q2, PROTUD-X9M4
    """
    # Caracteres que NO se confunden al leerlos:
    # Sin O (letra O) porque se confunde con 0 (cero)
    # Sin I (letra i) porque se confunde con 1 (uno)
    # Sin L porque se confunde con 1 también
    caracteres = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    # secrets.choice = elige 1 caracter al azar, de forma segura
    # for _ in range(4) = repetimos 4 veces
    # "".join(...) = juntamos los 4 caracteres en un texto
    parte = "".join(secrets.choice(caracteres) for _ in range(4))

    # f"PROTUD-{parte}" = pegamos el prefijo + la parte aleatoria
    return f"PROTUD-{parte}"

@app.route("/mis-robots")
@login_required
def mis_robots():
    """
    Página "Mis Robots".

    Muestra:
    - Los robots que puedo ver (los míos)
    - Un form para unirme con un código
    - Si soy admin, los códigos que creé para cada robot
    """
    usuario = session["usuario"]

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:

                # ------------------------------------------------
                # 1. Mis robots
                # ------------------------------------------------
                # Admin: ve todos los robots de la tabla robots
                # Operador: solo los que tiene en robot_usuarios
                if usuario["rol"] == "administrador":
                    cursor.execute("SELECT id, nombre FROM robots ORDER BY id")
                else:
                    # JOIN = juntamos robots + robot_usuarios
                    # WHERE ru.usuario_id = mi id = solo los míos
                    cursor.execute(
                        """
                        SELECT r.id, r.nombre
                        FROM robots AS r
                        JOIN robot_usuarios AS ru ON ru.robot_id = r.id
                        WHERE ru.usuario_id = %s
                        ORDER BY r.id
                        """,
                        (usuario["id"],),
                    )
                mis_robots_lista = cursor.fetchall()

                # ------------------------------------------------
                # 2. Mis invitaciones (solo si soy admin)
                # ------------------------------------------------
                # Muestro los códigos activos que creé, para poder
                # copiarlos o revocarlos
                # inv = (id, codigo, nombre_robot, vence_en, usos_max, usos_actuales, activo)
                invitaciones = []
                if usuario["rol"] == "administrador":
                    cursor.execute(
                        """
                        SELECT
                            i.id, i.codigo, r.nombre,
                            i.vence_en, i.usos_max, i.usos_actuales, i.activo
                        FROM invitaciones AS i
                        JOIN robots AS r ON i.robot_id = r.id
                        WHERE i.creado_por = %s
                        ORDER BY i.fecha_creacion DESC
                        LIMIT 20
                        """,
                        (usuario["id"],),
                    )
                    invitaciones = cursor.fetchall()

        return render_template(
            "mis_robots.html",
            robots=mis_robots_lista,
            invitaciones=invitaciones,
            usuario=usuario,
        )

    except psycopg.Error:
        app.logger.exception("Error en Mis Robots")
        return "No se pudieron cargar tus robots.", 500

@app.route("/robots/<int:robot_id>/invitar", methods=["POST"])
@login_required
def crear_invitacion(robot_id):
    """
    Crea un código de invitación para un robot.

    Solo lo puede hacer quien puede ver ese robot.
    En la práctica, lo hace el admin / dueño.

    El código que crea:
    - Vence en 24 horas
    - Se puede usar hasta 5 veces
    - Se puede revocar desde Mis Robots
    """
    usuario = session["usuario"]

    # -----------------------------------------------------------
    # Permiso: ¿puede ver este robot?
    # -----------------------------------------------------------
    # Si no puede ver el robot, tampoco puede invitar a otros.
    if not usuario_puede_ver_robot(usuario["id"], usuario["rol"], robot_id):
        return "No tenés permiso para este robot.", 403

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:

                # Generamos código único (ej: PROTUD-K7Q2)
                codigo = generar_codigo_invitacion()

                # Vence en 24 horas desde ahora
                # datetime.now() = ahora
                # timedelta(hours=24) = +24 horas
                vence = datetime.now() + timedelta(hours=24)

                # Guardamos la invitación
                # usos_max = 5 (hasta 5 personas)
                # usos_actuales = 0 (todavía nadie lo usó)
                # activo = TRUE (todavía sirve)
                cursor.execute(
                    """
                    INSERT INTO invitaciones
                        (codigo, robot_id, creado_por, vence_en, usos_max, usos_actuales, activo)
                    VALUES
                        (%s, %s, %s, %s, 5, 0, TRUE)
                    RETURNING id
                    """,
                    (codigo, robot_id, usuario["id"], vence),
                )

        # Volvemos a Mis Robots, ya va a aparecer el código nuevo
        return redirect(url_for("mis_robots"))

    except psycopg.Error:
        app.logger.exception("Error al crear invitación")
        return "No se pudo crear la invitación.", 500

@app.route("/unirse", methods=["POST"])
@login_required
def unirse_con_codigo():
    """
    El usuario pega un código y se une a ese robot.

    Ejemplo: pega PROTUD-K7Q2

    Pasos:
    1. Buscamos el código en invitaciones
    2. Revisamos que esté activo, que no haya vencido y que le queden usos
    3. Revisamos que no esté ya unido a ese robot
    4. Creamos la fila en robot_usuarios
    5. Sumamos 1 a usos_actuales
    """
    usuario = session["usuario"]

    # El código viene del form de Mis Robots
    # .upper() = si escribe protud-k7q2 en minúscula, igual anda
    # .strip() = saca espacios de más adelante y atrás
    codigo = (request.form.get("codigo") or "").strip().upper()

    if not codigo:
        return "Escribí un código.", 400

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:

                # ------------------------------------------------
                # 1. Buscar el código
                # ------------------------------------------------
                # Si no existe, inv = None
                cursor.execute(
                    """
                    SELECT id, robot_id, vence_en, usos_max, usos_actuales, activo
                    FROM invitaciones
                    WHERE codigo = %s
                    """,
                    (codigo,),
                )
                inv = cursor.fetchone()

                if not inv:
                    return "Código inválido.", 404

                # Desarmamos la tupla en variables con nombre
                inv_id, robot_id, vence_en, usos_max, usos_actuales, activo = inv

                # ------------------------------------------------
                # 2. Validar: activo, no vencido, con usos libres
                # ------------------------------------------------
                # Si el admin lo revocó, activo = False
                if not activo:
                    return "Este código fue revocado.", 403

                # Si la fecha de vencimiento ya pasó, no sirve
                if vence_en < datetime.now():
                    return "Este código venció.", 403

                # Si ya lo usaron 5 veces, no quedan usos
                if usos_actuales >= usos_max:
                    return "Este código ya se usó muchas veces.", 403

                # ------------------------------------------------
                # 3. ¿Ya está unido?
                # ------------------------------------------------
                # Si ya está en robot_usuarios, no lo agregamos de nuevo
                cursor.execute(
                    """
                    SELECT 1 FROM robot_usuarios
                    WHERE robot_id = %s AND usuario_id = %s
                    """,
                    (robot_id, usuario["id"]),
                )
                if cursor.fetchone():
                    return redirect(url_for("mis_robots"))

                # ------------------------------------------------
                # 4. Unirlo: crear fila en robot_usuarios
                # ------------------------------------------------
                # Esta fila es la que después usa usuario_puede_ver_robot()
                # para darle acceso al chat de ese robot.
                cursor.execute(
                    """
                    INSERT INTO robot_usuarios (robot_id, usuario_id)
                    VALUES (%s, %s)
                    """,
                    (robot_id, usuario["id"]),
                )

                # ------------------------------------------------
                # 5. Sumar 1 uso al código
                # ------------------------------------------------
                # Así, cuando llegue a 5, ya no sirve más.
                cursor.execute(
                    """
                    UPDATE invitaciones
                    SET usos_actuales = usos_actuales + 1
                    WHERE id = %s
                    """,
                    (inv_id,),
                )

        return redirect(url_for("mis_robots"))

    except psycopg.Error:
        app.logger.exception("Error al unirse con código")
        return "No se pudo unir al robot.", 500

@app.route("/invitaciones/<int:inv_id>/revocar", methods=["POST"])
@login_required
def revocar_invitacion(inv_id):
    """
    Revoca (anula) un código de invitación.

    Ejemplo: creaste PROTUD-K7Q2 y se filtró, lo revocás y ya nadie
    más lo puede usar, aunque no haya vencido.

    Revocar = poner activo = FALSE, no borrar la fila.
    Así queda registro de que existió.
    """
    usuario = session["usuario"]

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # Solo puedo revocar los códigos que creé yo,
                # salvo que sea admin (los admin pueden revocar cualquiera)
                if usuario["rol"] == "administrador":
                    cursor.execute(
                        "UPDATE invitaciones SET activo = FALSE WHERE id = %s",
                        (inv_id,),
                    )
                else:
                    # Si no soy admin, además pedimos creado_por = mi id
                    cursor.execute(
                        """
                        UPDATE invitaciones
                        SET activo = FALSE
                        WHERE id = %s AND creado_por = %s
                        """,
                        (inv_id, usuario["id"]),
                    )

        return redirect(url_for("mis_robots"))

    except psycopg.Error:
        app.logger.exception("Error al revocar invitación")
        return "No se pudo revocar.", 500

# ===============================================================
# CHAT
# ===============================================================

LARGO_MAXIMO_MENSAJE = 500
# LARGO_MAXIMO_MENSAJE = ningún mensaje puede tener más de 500 letras.
# Así evitamos mensajes gigantes que rompan la base.

@app.route(
    "/chat",
    methods=["GET", "POST"],
)
@login_required
def chat():
    """
    Sistema de chat por robot.

    SEGURIDAD IMPORTANTE:

    Antes:
        /chat?robot=2

    permitía seleccionar cualquier robot siempre que
    el usuario estuviera logueado.

    Ahora:

        1. comprobamos login,
        2. obtenemos robot_id,
        3. comprobamos permiso,
        4. recién después consultamos mensajes.
    """

    usuario = session["usuario"]

    # -----------------------------------------------------------
    # Obtener robot solicitado
    # -----------------------------------------------------------
    # request.values = busca en ?robot=1 (GET) y en form (POST)
    # type=int = lo convierte a número. Si no es número, da error.

    robot_id = request.values.get(
        "robot",
        1,  # Si no viene nada, por defecto robot 1
        type=int,
    )

    # Evitamos IDs inválidos.
    if robot_id <= 0:
        return "Robot inválido.", 400

    # -----------------------------------------------------------
    # COMPROBACIÓN DE PERMISOS
    # -----------------------------------------------------------

    if not usuario_puede_ver_robot(
        usuario["id"],
        usuario["rol"],
        robot_id,
    ):

        return (
            "No tenés permiso para acceder "
            "al chat de este robot.",
            403,
        )

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # ------------------------------------------------
                # POST
                # ------------------------------------------------
                # Este POST queda por compatibilidad con el form viejo.
                # El chat nuevo usa /api/chat/enviar, pero si alguien
                # manda un POST acá, también lo guardamos.

                if request.method == "POST":

                    texto = (
                        request.form
                        .get("texto", "")
                        .strip()  # .strip() = saca espacios de más
                    )

                    if texto:

                        cursor.execute(
                            """
                            INSERT INTO mensajes
                                (
                                    robot_id,
                                    usuario_id,
                                    texto
                                )
                            VALUES
                                (
                                    %s,
                                    %s,
                                    %s
                                )
                            """,
                            (
                                robot_id,
                                usuario["id"],
                                texto[:LARGO_MAXIMO_MENSAJE],
                            ),
                        )

                    return redirect(
                        url_for(
                            "chat",
                            robot=robot_id,
                        )
                    )

                # ------------------------------------------------
                # GET
                # ------------------------------------------------

                # Solo obtenemos robots que el usuario puede ver.
                if usuario["rol"] == "administrador":

                    cursor.execute(
                        """
                        SELECT
                            id,
                            nombre
                        FROM robots
                        ORDER BY id
                        """
                    )

                else:

                    cursor.execute(
                        """
                        SELECT
                            r.id,
                            r.nombre
                        FROM robots AS r
                        JOIN robot_usuarios AS ru
                            ON ru.robot_id = r.id
                        WHERE ru.usuario_id = %s
                        ORDER BY r.id
                        """,
                        (usuario["id"],),
                    )

                robots = cursor.fetchall()

                # ------------------------------------------------
                # Obtener mensajes
                # ------------------------------------------------
                # m.activo = TRUE = solo los que no fueron borrados

                cursor.execute(
                    """
                    SELECT
                        m.id,
                        m.texto,
                        m.fecha,
                        u.nombre,
                        m.usuario_id
                    FROM mensajes AS m
                    JOIN usuarios AS u
                        ON m.usuario_id = u.id
                    WHERE
                        m.robot_id = %s
                        AND m.activo
                    ORDER BY m.fecha ASC
                    """,
                    (robot_id,),
                )

                mensajes = cursor.fetchall()

        return render_template(
            "chat.html",
            robots=robots,
            robot_id=robot_id,
            mensajes=mensajes,
            usuario=usuario,
        )

    except psycopg.Error:

        app.logger.exception(
            "Error en el chat"
        )

        return (
            "No se pudo cargar el chat.",
            500,
        )

# ===============================================================
# API DEL CHAT EN VIVO
# ===============================================================
# ¿Para qué es esto?
# Tu chat actual funciona con POST + redirect: cada mensaje recarga
# toda la página. Anda, pero es lento y molesto.
#
# Con esta API, el JavaScript de chat.html pregunta cada 2 segundos:
#   "¿hay mensajes nuevos para el robot 1?"
# Y si hay, los dibuja sin recargar la página.
#
# Son 2 rutas:
#   GET  /api/chat/mensajes?robot=1 -> devuelve los mensajes en JSON
#   POST /api/chat/enviar            -> guarda un mensaje nuevo

@app.route("/api/chat/mensajes")
@login_required
def api_chat_mensajes():
    """
    Devuelve los mensajes de un robot en formato JSON.

    Ejemplo de lo que devuelve:
    {
      "mensajes": [
        {"id": 5, "texto": "Voy yo", "fecha": "10:05", "nombre": "Ariel", "es_mio": true}
      ]
    }

    SEGURIDAD: usa el mismo permiso que /chat.
    Sin esto, cualquiera podría leer el chat de otro robot
    pegando /api/chat/mensajes?robot=2 en el navegador.
    """

    usuario = session["usuario"]

    # ¿De qué robot pide mensajes? Por defecto robot 1
    robot_id = request.args.get("robot", 1, type=int)

    # Si el robot no existe o es inválido, frenamos
    if robot_id <= 0:
        return "Robot inválido.", 400

    # -----------------------------------------------------------
    # Permiso: ¿puede ver este robot?
    # -----------------------------------------------------------
    # Admin: sí, todos.
    # Operador: solo si está en robot_usuarios para ese robot.
    if not usuario_puede_ver_robot(
        usuario["id"],
        usuario["rol"],
        robot_id,
    ):
        return "No tenés permiso para este robot.", 403

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                # Traemos los mensajes activos (activo = TRUE)
                # Los borrados tienen activo = FALSE y no se muestran
                cursor.execute(
                    """
                    SELECT
                        m.id,
                        m.texto,
                        m.fecha,
                        u.nombre,
                        m.usuario_id
                    FROM mensajes AS m
                    JOIN usuarios AS u
                        ON m.usuario_id = u.id
                    WHERE
                        m.robot_id = %s
                        AND m.activo
                    ORDER BY m.fecha ASC
                    """,
                    (robot_id,),
                )

                filas = cursor.fetchall()

        # -------------------------------------------------------
        # Convertimos las filas a JSON
        # -------------------------------------------------------
        # es_mio = True si el mensaje lo escribí yo.
        # Sirve para pintarlo de otro color en el chat (azul).
        # fecha la pasamos a "HH:MM" para que se vea lindo.
        salida = []
        for id_m, texto, fecha, nombre, autor_id in filas:
            salida.append({
                "id": id_m,
                "texto": texto,
                "fecha": fecha.strftime("%H:%M"),
                "nombre": nombre,
                "es_mio": autor_id == usuario["id"],
            })

        return {"mensajes": salida}

    except psycopg.Error:

        app.logger.exception("Error en API del chat")
        return "No se pudo cargar el chat.", 500

@app.route("/api/chat/enviar", methods=["POST"])
@login_required
def api_chat_enviar():
    """
    Guarda un mensaje que viene del JavaScript, sin recargar la página.

    El JS manda algo así:
    {
      "texto": "Voy al pasillo",
      "robot": 1
    }

    Devuelve:
    {"id": 11} con código 201 (creado)
    """

    usuario = session["usuario"]

    # request.get_json() lee el JSON que mandó el JS
    datos = request.get_json() or {}

    # Limpiamos espacios y cortamos a 500 caracteres
    texto = (datos.get("texto") or "").strip()[:LARGO_MAXIMO_MENSAJE]
    robot_id = int(datos.get("robot", 1))

    # -----------------------------------------------------------
    # Permiso también al enviar
    # -----------------------------------------------------------
    # No alcanza con controlar al leer: también hay que controlar
    # al escribir, si no podría escribir en un robot que no es mío.
    if not usuario_puede_ver_robot(
        usuario["id"],
        usuario["rol"],
        robot_id,
    ):
        return "No tenés permiso para este robot.", 403

    # Si el mensaje está vacío, no guardamos nada
    if not texto:
        return "Escribí algo.", 400

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO mensajes
                        (robot_id, usuario_id, texto)
                    VALUES
                        (%s, %s, %s)
                    RETURNING id
                    """,
                    (robot_id, usuario["id"], texto),
                )

                nuevo_id = cursor.fetchone()[0]

        # 201 = creado correctamente
        return jsonify({"id": nuevo_id}), 201

    except psycopg.Error:

        app.logger.exception("Error al enviar mensaje")
        return "No se pudo enviar el mensaje.", 500

# ===============================================================
# BORRAR MENSAJE
# ===============================================================

@app.route(
    "/chat/mensajes/<int:mensaje_id>/borrar",
    methods=["POST"],
)
@login_required
def borrar_mensaje(mensaje_id):
    """
    Baja lógica de un mensaje.

    Un operador:
        solo puede borrar sus propios mensajes.

    Un administrador:
        puede borrar cualquiera.

    Baja lógica = poner activo = FALSE, no borrar la fila.
    """

    usuario = session["usuario"]

    robot_id = request.form.get(
        "robot",
        1,
        type=int,
    )

    # Primero comprobamos que el usuario pueda
    # acceder al robot indicado.
    if not usuario_puede_ver_robot(
        usuario["id"],
        usuario["rol"],
        robot_id,
    ):

        return (
            "No tenés permiso para este robot.",
            403,
        )

    try:

        with conectar_db() as conexion:

            with conexion.cursor() as cursor:

                if usuario["rol"] == "administrador":

                    # Admin: puede borrar cualquier mensaje
                    cursor.execute(
                        """
                        UPDATE mensajes
                        SET activo = FALSE
                        WHERE id = %s
                        """,
                        (mensaje_id,),
                    )

                else:

                    # Operador: solo los suyos, y solo de ese robot
                    cursor.execute(
                        """
                        UPDATE mensajes
                        SET activo = FALSE
                        WHERE
                            id = %s
                            AND usuario_id = %s
                            AND robot_id = %s
                        """,
                        (
                            mensaje_id,
                            usuario["id"],
                            robot_id,
                        ),
                    )

        return redirect(
            url_for(
                "chat",
                robot=robot_id,
            )
        )

    except psycopg.Error:

        app.logger.exception(
            "No se pudo borrar el mensaje"
        )

        return (
            "No se pudo borrar el mensaje.",
            500,
        )

# ===============================================================
# CIERRE DE SESIÓN
# ===============================================================

@app.route("/logout")
def logout():
    """
    Cierra completamente la sesión actual.
    Borra todo lo que había en session.
    """

    session.clear()

    return redirect(
        url_for("inicio")
    )

# ===============================================================
# WEBHOOK DE TELEGRAM - /webhook
# ===============================================================
# ¿Qué es un webhook?
# En vez de que nuestro bot pregunte cada 2 segundos
# "¿hay mensajes nuevos?", Telegram NOS AVISA cuando llega uno.
# Telegram hace POST a https://tu-pagina.onrender.com/webhook
# con el mensaje, y acá lo procesamos.
#
# ¿Por qué acá y no en bot.py?
# Porque así usamos el mismo Web Service gratis de Render.
# No necesitamos un Background Worker pago.
# Y guarda en la MISMA base de Render, no en la de tu compu.

# Leemos el token de las variables de entorno de Render.
# En Render tiene que estar: TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Armamos la URL base de la API de Telegram con ese token
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def mandar_mensaje_telegram(chat_id, texto):
    """
    Manda un mensaje de texto a un chat de Telegram.
    chat_id = a quién (el número que Telegram le da a cada persona)
    texto = qué le decimos
    """
    # Si no hay token, no podemos mandar nada, salimos sin romper
    if not TELEGRAM_BOT_TOKEN:
        print("Falta TELEGRAM_BOT_TOKEN en Render, no puedo mandar mensaje")
        return
    try:
        # POST a sendMessage = Telegram manda el mensaje
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": texto},
            timeout=10,  # Si en 10 seg no responde, cortamos
        )
    except Exception as e:
        # Si falla el envío, lo dejamos en los logs pero no rompemos la página
        print(f"Error mandando telegram: {e}")

@app.route("/webhook", methods=["POST"])
def webhook_telegram():
    """
    Recibe los mensajes que Telegram nos manda.
    Cuando alguien manda /start, lo suscribimos.
    """
    try:
        # request.get_json() = lo que Telegram nos mandó en JSON
        datos = request.get_json() or {}
        # message = el mensaje (puede no venir si es otro tipo de evento)
        mensaje = datos.get("message", {})
        # text = lo que escribió, ej: "/start"
        texto = (mensaje.get("text") or "").strip()
        # chat = a quién le tenemos que responder
        chat = mensaje.get("chat", {})
        # chat_id = el ID único de esa persona en Telegram
        chat_id = chat.get("id")
        # Nombre para guardarlo lindo en la base
        nombre = f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
        # Si no tiene nombre, le ponemos el username o "Sin nombre"
        if not nombre:
            nombre = chat.get("username", "Sin nombre")

        # Solo nos interesa /start y que venga con chat_id
        if texto == "/start" and chat_id:
            # Guardamos en la base de Render con conectar_db()
            # Esta es la misma función que usa toda la app, por eso
            # guarda en la misma base que ve la página.
            with conectar_db() as conexion:
                with conexion.cursor() as cursor:
                    # INSERT ... ON CONFLICT = si ya existe ese chat_id,
                    # no crea otro, solo lo reactiva y actualiza el nombre.
                    # Así Braian puede mandar /start 10 veces y no se duplica.
                    cursor.execute(
                        """
                        INSERT INTO suscriptores_telegram (chat_id, nombre, activo)
                        VALUES (%s, %s, TRUE)
                        ON CONFLICT (chat_id)
                        DO UPDATE SET nombre = EXCLUDED.nombre, activo = TRUE
                        """,
                        (int(chat_id), nombre),  # int() porque en la base chat_id es bigint, no text
                    )
            print(f"GUARDADO WEBHOOK: {chat_id} - {nombre}")
            # Le respondemos que ya quedó suscripto
            mandar_mensaje_telegram(
                chat_id,
                "✅ ¡Listo! Ya estás suscripto a las alertas de PROTUD. Vas a recibir alertas solo cuando tus robots se caigan."
            )

        # Siempre devolvemos "ok" para que Telegram no reintente
        return "ok", 200
    except Exception as e:
        # Si algo falla, lo mostramos en los logs de Render
        # y igual devolvemos "ok" para que Telegram no nos spamee
        print(f"Error webhook: {e}")
        return "ok", 200

# ===============================================================
# INICIAR SERVIDOR
# ===============================================================

if __name__ == "__main__":

    # Para desarrollo local.
    #
    # IMPORTANTE:
    # debug=True NO debe utilizarse en producción.
    # En producción, Render corre la app con gunicorn.
    app.run(debug=True)