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
- Bot de Telegram por Webhook (gratis, sin Background Worker).

SEGURIDAD:

- Las páginas privadas requieren iniciar sesión.
- Las páginas administrativas requieren rol "administrador".
- El chat comprueba que el usuario tenga permiso sobre el robot.
- No se confía únicamente en el parámetro ?robot=...
- Las cookies de sesión son HttpOnly y SameSite=Lax.
- En producción la cookie es Secure (solo HTTPS).
- El login con Google usa OAuth 2.0 + OpenID Connect.
- Las bajas son lógicas, nunca se borra la fila de la base.

ARCHIVOS QUE USA ESTA APP:

- app.py                  -> este archivo, toda la lógica web + webhook
- telegram_service.py     -> funciones para mandar alertas y fotos a Telegram
- templates/*.html        -> las páginas (index, panel, chat, mis_robots, etc)
- static/*                -> css, js, imágenes
- .env                    -> secretos (SECRET_KEY, GOOGLE_*, DATABASE_URL, TELEGRAM_BOT_TOKEN)

CÓMO CORRE:

- En tu compu: python app.py -> http://127.0.0.1:5000
- En Render: gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT
  IMPORTANTE: tiene que ser --workers 1. Si ponés 2 o más, la sesión de
  Google se pierde entre workers y te tira MismatchingStateError.

"""

# ==============================================================================
# LIBRERÍAS
# ==============================================================================
# Librerías = herramientas que importamos para usar después.
# Si falta alguna, el programa no arranca.
# Cada import tiene su comentario para que sepas para qué sirve.
# ==============================================================================

import os
# os = para leer variables de entorno (SECRET_KEY, DATABASE_URL, etc.)
# Las variables de entorno son datos secretos que están en .env,
# no escritos en el código.
# Ejemplo: os.getenv("SECRET_KEY") -> lee la clave del .env o de Render.
# Si no existe, devuelve None.

from pathlib import Path
# Path = para armar rutas de archivos (ej: dónde está el .env)
# Path(__file__) = este archivo app.py
# .resolve().parent = la carpeta donde está app.py
# / ".env" = le agregamos el archivo .env
# Así anda igual en Windows y en Linux / Render.

from functools import wraps
# wraps = para que los decoradores @login_required no rompan
# el nombre de la función original.
# Sin wraps, Flask se confunde porque todas las funciones
# se llamarían "wrapper" y te tira error de "View function mapping".

import psycopg
# psycopg = librería para hablar con PostgreSQL (la base de datos)
# psycopg.connect(...) = abre conexión
# with conectar_db() as conexion: = abre y cierra solo
# with conexion.cursor() as cursor: = para ejecutar SQL
# cursor.execute("SELECT ...", (dato,)) = ejecuta SQL con parámetros seguros
# cursor.fetchone() = trae 1 fila
# cursor.fetchall() = trae todas las filas
# Usamos %s para parámetros, NUNCA f-string con datos del usuario,
# porque si no te hacen SQL Injection.

# -----------------------------------------------------------------------------
# NUEVO - ETAPA 2: para los códigos de invitación
# -----------------------------------------------------------------------------
import secrets
# secrets = para generar códigos aleatorios seguros.
# No usamos random porque secrets es más difícil de adivinar.
# secrets.choice("ABC...") = elige 1 caracter al azar de forma segura.
# Es el que usa Python para contraseñas y tokens.

import string
# string = tiene las letras y números.
# string.ascii_uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# string.digits = "0123456789"
# Acá lo dejamos importado por si querés cambiar el alfabeto del código.
# Hoy usamos un alfabeto manual sin O, 0, I, 1, L para no confundir.

from datetime import datetime, timedelta
# datetime = para saber la fecha/hora actual (ej: ahora)
# datetime.now() = ahora, sin zona horaria
# datetime.now() + timedelta(hours=24) = ahora + 24 horas
# timedelta = para sumar tiempo (ej: ahora + 24 horas = cuándo vence el código)
# timedelta(hours=12) = 12 horas, lo usamos para la sesión permanente.
# timedelta(days=7) = 7 días, por si querés códigos que duren 1 semana.

from dotenv import load_dotenv
# load_dotenv = lee el archivo .env y carga las variables
# load_dotenv(Path(...) / ".env") = busca el .env al lado de app.py
# En Render no hay .env, las variables vienen de Environment.
# load_dotenv no rompe si no hay .env, simplemente no carga nada.

from flask import (
    Flask,           # Flask = para crear la aplicación web
    render_template, # render_template = para mostrar un .html
    redirect,        # redirect = para mandar a otra página (ej: después de borrar)
    url_for,         # url_for = busca la URL de una función (ej: url_for('panel') -> /panel)
    session,         # session = cajita donde guardamos quién está logueado
    request,         # request = lo que manda el navegador (form, ?robot=1, JSON)
    jsonify,         # jsonify = para devolver JSON en la API del chat
    flash,           # flash = para mostrar mensajitos tipo "Código inválido" en la web
    # flash("Mensaje", "success") = guarda mensaje para mostrar en el próximo render
    # En mis_robots.html hay que mostrarlo con get_flashed_messages()
    # Si tu template no lo muestra, el mensaje se guarda pero no se ve.
    # Por eso también dejamos el redirect, para que no quede en blanco.
)
# Flask = micro-framework web.
# render_template("panel.html", pendientes=...) = busca panel.html en templates/
# y le pasa variables para usar con {{ pendientes }} en el HTML.
# redirect(url_for("panel")) = manda al navegador a otra URL.
# session = dict especial que Flask guarda en una cookie firmada.
# session["usuario"] = {"id": 1, "nombre": "Ariel", ...}
# request.form = datos de un <form method="POST">
# request.args = datos de ?robot=1 en la URL
# request.values = busca en form + args juntos
# request.get_json() = lee JSON que manda el JS con fetch()
# jsonify({"id": 11}) = devuelve {"id": 11} con Content-Type application/json

from werkzeug.middleware.proxy_fix import ProxyFix
# ProxyFix = para que Flask entienda que está detrás de Render / proxy
# Render recibe https:// y le pasa a Flask http:// por dentro.
# Sin ProxyFix, Flask cree que estás en http:// y:
# - url_for(..., _external=True) genera http:// en vez de https://
# - Google compara http vs https y dice "State not equal"
# - Te tira MismatchingStateError y no podés entrar.
# Por eso ProxyFix es OBLIGATORIO en Render.
# x_proto=1 = confía en el header X-Forwarded-Proto que manda Render
# x_host=1 = confía en X-Forwarded-Host
# x_for=1 = confía en X-Forwarded-For (IP real)
# x_prefix=1 = confía en X-Forwarded-Prefix

from authlib.integrations.flask_client import OAuth
# OAuth = para el login con Google
# OAuth(app) = crea el cliente OAuth atado a Flask
# oauth.register(name="google", ...) = registra Google como proveedor
# google.authorize_redirect(...) = te manda a Google
# google.authorize_access_token() = cuando Google vuelve, valida el token
# token["userinfo"] = datos que Google nos da: name, email, picture, sub

# CORRECCION - Para detectar el error de Google y no mostrar 401 feo
from authlib.integrations.base_client.errors import OAuthError
# OAuthError = clase padre de todos los errores de Authlib
# MismatchingStateError hereda de OAuthError
# Si lo atrapamos, podemos hacer session.clear() y mandar de nuevo a /login
# en vez de dejarte con una pantalla blanca de error.
# Antes: except Exception -> return 401 "No se pudo completar..."
# Ahora: except OAuthError -> redirect a login_google limpio

from telegram_service import (
    enviar_alerta_telegram,
    enviar_foto_telegram,
)
# telegram_service = archivo nuestro que manda mensajes a Telegram
# enviar_alerta_telegram(robot, evento, ubicacion) = manda texto
# enviar_foto_telegram(robot, evento, ubicacion, ruta_foto) = manda foto + texto
# Esas funciones usan TELEGRAM_BOT_TOKEN y CHAT_ID de .env / Render
# Si fallan, devuelven False, no rompen la página.

# -----------------------------------------------------------------------------
# NUEVO - BOT POR WEBHOOK (OPCIÓN 1 GRATIS)
# -----------------------------------------------------------------------------
# Antes el bot corría aparte con bot.py y polling.
# Eso en Render es pago (Background Worker).
# Ahora el bot vive adentro de esta misma página.
# Telegram le manda los mensajes a /webhook y acá los atendemos.
# Así no pagamos nada extra y anda aunque tu compu esté apagada.
# Flujo:
#   1. Usuario manda /start en Telegram
#   2. Telegram hace POST a https://tu-pagina.onrender.com/webhook
#   3. Nuestra función webhook_telegram() lo procesa
#   4. Guardamos en la base de Render
#   5. Respondemos con mandar_mensaje_telegram()
# Para que ande, en Telegram tenés que haber hecho 1 sola vez:
# https://api.telegram.org/botTU_TOKEN/setWebhook?url=https://TU-PAGINA.onrender.com/webhook
import requests
# requests = para mandar mensajes de vuelta a Telegram
# requests.post("https://api.telegram.org/bot.../sendMessage", json={...})
# También sirve para cualquier API externa.
# timeout=10 = si en 10 seg no responde, cortamos para no colgar la página.

# ==============================================================================
# CONFIGURACIÓN INICIAL
# ==============================================================================

# Cargar el .env que está junto a app.py
# .env tiene: SECRET_KEY, GOOGLE_CLIENT_ID, DATABASE_URL, etc.
load_dotenv(Path(__file__).resolve().parent / ".env")
# Si estás en Render, no hay .env, las variables vienen de Environment.
# load_dotenv no tira error si no encuentra .env.

# Crear aplicación Flask
# app es la aplicación web. Todas las rutas cuelgan de acá.
# @app.route("/") = cuando alguien entra a /, ejecuta la función de abajo.
app = Flask(__name__)
# __name__ = nombre del módulo actual, Flask lo usa para buscar templates/ y static/

# -----------------------------------------------------------------------------
# ProxyFix - CORREGIDO PARA EL ERROR DE GOOGLE
# -----------------------------------------------------------------------------
# Necesario cuando la aplicación está detrás de un proxy,
# como puede ocurrir en Render.
# Esto permite que Flask reconozca correctamente HTTPS y el host.
# Sin esto, MismatchingStateError SIEMPRE.
# CORRECCION: Antes solo tenías x_proto y x_host.
# Ahora agregamos x_for y x_prefix para que Render pase todo bien.
# -----------------------------------------------------------------------------
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1,
)
# wsgi_app = la aplicación WSGI que corre detrás de gunicorn.
# ProxyFix la envuelve y corrige los headers antes de que Flask los vea.

# ==============================================================================
# CONFIGURACIÓN DE SESIÓN - CORREGIDO
# ==============================================================================

# SECRET_KEY = clave secreta para firmar las cookies de sesión.
# Si alguien la conoce, puede falsificar sesiones.
# Ejemplo: puede hacerse pasar por admin sin loguearse.
# Por eso NUNCA la subas a GitHub en texto plano si el repo es público.
# En local va en .env. En Render va en Environment.
SECRET_KEY = os.getenv("SECRET_KEY")
# os.getenv("SECRET_KEY") = busca la variable SECRET_KEY
# Si no existe, devuelve None.

# Si no tenemos SECRET_KEY, es mejor detener la aplicación.
# Sin esta clave, las sesiones de Flask no están correctamente
# protegidas.
# Si te tira este error en Render, es porque no pusiste SECRET_KEY
# en Environment. Agregala y hacé Redeploy.
if not SECRET_KEY:
    raise RuntimeError(
        "Falta SECRET_KEY en el archivo .env"
    )
# RuntimeError = error que frena el arranque.
# Mejor frenar acá que arrancar sin protección.

app.secret_key = SECRET_KEY
# app.secret_key = la clave que Flask usa para firmar la cookie de sesión.
# La cookie dice: {"usuario": {...}} + firma con SECRET_KEY.
# Si alguien cambia la cookie, la firma no coincide y Flask la descarta.

# -----------------------------------------------------------------------------
# Cookies de sesión
# -----------------------------------------------------------------------------

# JavaScript del navegador no puede leer la cookie de sesión.
# Así, si hay un script malo, no te roba la sesión.
# Esto es HttpOnly = True.
app.config["SESSION_COOKIE_HTTPONLY"] = True
# HttpOnly = el JS con document.cookie no la ve.
# Solo el navegador la manda automáticamente en cada request.

# Evita que la cookie se envíe en la mayoría de peticiones
# cross-site (de otra página).
# SameSite=Lax = la cookie viaja cuando volvés de Google,
# pero no cuando otro sitio te hace un POST malicioso.
# Si ponés Strict, Google no te deja volver logueado porque
# el navegador no manda la cookie al volver de Google.
# Si ponés None, tenés que poner Secure=True sí o sí.
# Por eso Lax es el equilibrio correcto para login con Google.
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
# Si ponés Secure=True en local con http://, la cookie no se guarda
# y nunca quedás logueado. Por eso lo leemos de variable de entorno.
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
)
# os.getenv(..., "false") = si no hay variable, usa "false"
# .lower() == "true" = "True", "TRUE", "true" -> todos dan True
# En Render: SESSION_COOKIE_SECURE=true -> cookie solo por https, bien.
# En local: no hay variable -> false -> cookie por http, bien.

# CORRECCION - Para que Flask sepa que está en https aunque Render le pase http
# Sin esto, url_for(..., _external=True) genera http:// y Google lo rechaza.
app.config["PREFERRED_URL_SCHEME"] = "https"
# PREFERRED_URL_SCHEME = esquema preferido para generar URLs externas.
# En local no molesta porque igual entrás por http://127.0.0.1:5000
# y Flask usa el esquema de la request si no hay proxy.
# En Render con ProxyFix, ya viene https, esto es doble seguridad.

# CORRECCION - Para que la sesión no se borre cuando volvés de Google
# SESSION_PERMANENT = True = la sesión dura lo que dice PERMANENT_SESSION_LIFETIME
# Si es False, la sesión se borra cuando cerrás el navegador.
app.config["SESSION_PERMANENT"] = True
# PERMANENT_SESSION_LIFETIME = cuánto dura la sesión permanente
# 12 horas = entrás a la mañana y no tenés que loguearte a cada rato.
# Si querés que dure 7 días, poné timedelta(days=7)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

# ==============================================================================
# GOOGLE OAUTH
# ==============================================================================
# OAuth = sistema para loguearse con Google sin que nosotros
# guardemos la contraseña del usuario.
# Google nos dice: "sí, es Ariel, su email es..."
# Flujo completo:
#   1. Usuario aprieta "Entrar con Google" -> /login/google
#   2. Flask guarda un "state" en session y manda a Google
#   3. Google muestra "¿Querés entrar a Protud con tu cuenta?"
#   4. Usuario acepta -> Google vuelve a /callback con code + state
#   5. Flask compara state que guardó vs state que manda Google
#      Si no coinciden -> MismatchingStateError
#      ¿Cuándo no coinciden? Si la sesión se perdió en el medio.
#      Causas: 2 workers en Render, SECRET_KEY que cambia, cookie Secure mal.
#   6. Si coinciden, Flask pide token a Google y Google da userinfo
#   7. Buscamos o creamos usuario en la base y creamos session["usuario"]
#   8. Redirect a /panel

oauth = OAuth(app)
# OAuth(app) = crea el cliente OAuth atado a esta app Flask.
# Guarda el state en session automáticamente.

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),
    # server_metadata_url = Google publica acá sus URLs de login, token, etc.
    # Authlib las lee solo, no tenés que escribirlas a mano.
    client_kwargs={
        "scope": "openid email profile"
        # scope = qué datos pedimos: id, email y perfil (nombre)
        # openid = para usar OpenID Connect
        # email = para que nos dé el email
        # profile = para que nos dé nombre y foto
        # Si pedís más scopes, Google te pide más permisos y asusta al usuario.
    },
)
# google = cliente para hablar con Google.
# google.authorize_redirect(...) = te manda a Google
# google.authorize_access_token() = valida el código que trae Google

# ==============================================================================
# CONEXIÓN A POSTGRESQL
# ==============================================================================

def conectar_db():
    """
    Devuelve una conexión a PostgreSQL.

    En Render:
        usa DATABASE_URL

    En la computadora:
        usa DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD
        definidos en .env.

    Uso:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT ...")
                fila = cursor.fetchone()

    El with cierra solo la conexión aunque haya error.
    Si no usás with, tenés que hacer conexion.close() a mano.
    Si te olvidás, se acumulan conexiones y Render te tira
    "too many connections".

    connect_timeout=5 = si en 5 seg no conecta, da error.
    Sin timeout, se puede quedar colgado 30 seg y Render te da timeout.
    """
    database_url = os.getenv("DATABASE_URL")
    # DATABASE_URL en Render es algo como:
    # postgres://usuario:clave@dpg-...:5432/protud_db
    # Ya trae todo junto: usuario, clave, host, puerto, base.

    if database_url:
        # En Render, DATABASE_URL ya trae todo junto
        return psycopg.connect(
            database_url,
            connect_timeout=5  # Si en 5 seg no conecta, da error
        )

    # En local, armamos la conexión con los datos sueltos
    # En tu .env local tenés que tener:
    # DB_HOST=localhost
    # DB_PORT=5432
    # DB_NAME=protud
    # DB_USER=postgres
    # DB_PASSWORD=tu_clave
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )

# ==============================================================================
# FUNCIONES DE SEGURIDAD
# ==============================================================================

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

    Cómo funciona:
        - @wraps(func) = para que Flask no pierda el nombre de la función.
        - wrapper(*args, **kwargs) = función que reemplaza a la original.
        - session.get("usuario") = ¿hay alguien logueado?
        - Si no hay, redirect a login_google.
        - Si hay, ejecuta la función original con sus args.

    Si no ponés @login_required en una ruta privada, cualquiera
    que pegue la URL puede entrar sin loguearse. Por eso todas
    las rutas privadas lo tienen.
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
    Si no está logueado, lo manda a login.

    Ejemplo:
        @app.route("/usuarios")
        @admin_required
        def usuarios(): ...

    Roles:
        - administrador: puede ver todo, dar de baja, cambiar roles,
                         crear invitaciones, ver /probar-db, /probar-telegram
        - operador: solo puede ver sus robots, su chat, sus alertas.
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

    Parámetros:
        usuario_id = id del usuario logueado (de session["usuario"]["id"])
        rol = "administrador" o "operador"
        robot_id = id del robot que quiere ver

    Devuelve:
        True = puede verlo
        False = no puede verlo

    Se usa en:
        - /chat
        - /api/chat/mensajes
        - /api/chat/enviar
        - /chat/mensajes/<id>/borrar
        - /robots/<id>/invitar
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

# ==============================================================================
# PÁGINA PRINCIPAL
# ==============================================================================

# CORRECCION - Acá estaba tu error más grande.
# antes tenia:
# <<<<<<< HEAD
#     return render_template("index.html")
# =======
#     return render_template("index.html", usuario=...)
# >>>>>>> 9314311a...
# Eso es un CONFLICTO DE GIT sin resolver. Git te deja esas marcas
# cuando dos personas (o vos en dos compus) cambian lo mismo.
# Python no entiende <<<<<<< y te tira SyntaxError y no arranca nada.
# AHORA: dejamos solo la versión buena, la que manda usuario=...
@app.route("/")
def inicio():
    """
    Página pública principal.

    Mostrar la portada no necesita login.
    Pero le mandamos usuario=session.get("usuario") para que index.html
    sepa si estás logueado y te muestre:
    - Si estás logueado: "Hola Ariel" + botón "Ir al panel"
    - Si no estás logueado: botón "Entrar con Google"

    Si no le mandás usuario, index.html tira error de variable no definida
    o te muestra siempre el botón de login aunque ya estés adentro.
    """
    usuario = session.get("usuario")
    if usuario:
        session["bienvenida_vista"] = True
    return render_template("index.html", usuario=usuario)

# ==============================================================================
# PANEL
# ==============================================================================

@app.route("/panel")
@login_required
def panel():
    """
    Panel principal.

    SOLO usuarios logueados.
    Muestra: alertas pendientes, alertas últimas 24h,
    cantidad de fotos y las últimas 5 alertas.

    Consultas:
        - COUNT(*) FILTER (WHERE NOT atendida) = pendientes
        - COUNT(*) FILTER (WHERE fecha_hora >= NOW() - 24h) = últimas 24h
        - COUNT(foto_url) = cuántas tienen foto
        - SELECT ... ORDER BY fecha_hora DESC LIMIT 5 = últimas 5
    """
        # Usuario nuevo (operador sin robots): primero la bienvenida
    usuario = session["usuario"]
    if usuario["rol"] != "administrador" and not session.get("bienvenida_vista"):
        try:
            with conectar_db() as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM robot_usuarios WHERE usuario_id = %s LIMIT 1",
                        (usuario["id"],),
                    )
                    tiene_robots = cursor.fetchone() is not None
        except psycopg.Error:
            tiene_robots = True
        if not tiene_robots:
            return redirect(url_for("inicio"))

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

# ==============================================================================
# ROBOT
# ==============================================================================

@app.route("/robot")
@login_required
def robot():
    """
    Página que muestra la última alerta del robot.

    También queda protegida porque contiene información
    del sistema.

    LIMIT 1 = solo la última alerta, no todas.
    ORDER BY fecha_hora DESC = la más nueva primero.
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

# ==============================================================================
# CONTROL
# ==============================================================================

@app.route("/control")
@login_required
def control():
    """
    Página de control del robot.

    Queda protegida porque podría contener controles
    que no deben estar disponibles públicamente.
    """
    return render_template("control.html")

# ==============================================================================
# FOTOS
# ==============================================================================

@app.route("/fotos")
@login_required
def fotos():
    """
    Fotos del robot.

    IMPORTANTE:
    Actualmente las fotos son de ejemplo.
    Cuando el robot real mande fotos, acá hay que leer de la base
    la tabla alertas donde foto_url IS NOT NULL.
    Por ahora dejamos 3 de ejemplo para que la página no quede vacía.
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

# ==============================================================================
# PRUEBA DE BASE DE DATOS
# ==============================================================================

@app.route("/probar-db")
@admin_required
def probar_db():
    """
    Ruta de diagnóstico.

    Solo administrador.

    No conviene dejar endpoints de diagnóstico públicos.
    Si un operador entra, le da 403 por @admin_required.
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

# ==============================================================================
# ALERTAS
# ==============================================================================

@app.route("/alertas")
@login_required
def ver_alertas():
    """
    Muestra todas las alertas.

    Antes esta ruta podía abrirse directamente sin login.
    Ahora tiene @login_required.

    JOIN = juntamos alertas + robots para saber el nombre del robot.
    Sin JOIN, solo tendríamos robot_id = 1, pero no sabríamos
    que se llama "Mini Protud".
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

# ==============================================================================
# ATENDER ALERTA
# ==============================================================================

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
    Si fuera GET, cualquiera que pegue el link la atendería sin querer.

    <int:alerta_id> = Flask convierte a int automáticamente.
    Si ponés /alertas/abc/atender, Flask da 404 porque abc no es int.
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

# ==============================================================================
# DESHACER ALERTA
# ==============================================================================

@app.route(
    "/alertas/<int:alerta_id>/deshacer",
    methods=["POST"],
)
@login_required
def deshacer_alerta(alerta_id):
    """
    Vuelve una alerta a estado pendiente.
    Es lo contrario de atender.
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

# ==============================================================================
# NOTIFICACIONES
# ==============================================================================

@app.route("/notificaciones")
@login_required
def ver_notificaciones():
    """
    Lista las notificaciones enviadas por Telegram.

    Antes podía consultarse sin autenticación.
    Ahora tiene @login_required.
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

# ==============================================================================
# PRUEBA TELEGRAM
# ==============================================================================

@app.route("/probar-telegram")
@admin_required
def probar_telegram_flask():
    """
    Prueba manual de Telegram.

    Solo administrador.
    Manda un mensaje de prueba a todos los suscriptores.
    Si te llega, el bot anda. Si no te llega, revisá TELEGRAM_BOT_TOKEN.
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

# ==============================================================================
# REGISTRAR NOTIFICACIÓN
# ==============================================================================

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

    Parámetros:
        alerta_id = id de la alerta que generó la notificación
        mensaje = texto que se mandó a Telegram
        enviado = True si Telegram lo aceptó, False si falló

    Devuelve:
        id de la notificación creada (RETURNING id)
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

# ==============================================================================
# SIMULAR ALERTA
# ==============================================================================

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

    Pasos:
        1. Crear alerta en PostgreSQL (INSERT INTO alertas)
        2. Mandar foto de prueba a Telegram (enviar_foto_telegram)
        3. Registrar resultado (registrar_notificacion)

    Devuelve JSON:
        {"alerta_id": 1, "notificacion_id": 1, "registrada": True, "telegram_enviado": True}
    Con código 201 = creado correctamente.
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

# ==============================================================================
# LOGIN CON GOOGLE - CORRECCION 1
# ==============================================================================
# CORRECCION:
# Antes solo existia /login/google. Si tu boton en index.html
# decia /login, daba 404 y no aparecia Google.
# Ahora agregamos /login que redirige a /login/google.
# Andan las 2 rutas.

@app.route("/login")
def login():
    """
    Atajo para el boton de login.

    Si el boton dice /login, viene aca y lo manda
    a /login/google que es el verdadero login con Google.
    """
    return redirect(
        url_for("login_google")
    )

@app.route("/login/google")
def login_google():
    """
    Envía al usuario a Google para autenticarse.

    CORRECCION - Antes no limpiaba el state viejo.
    Si apretabas 2 veces "Entrar con Google" sin terminar el primero,
    quedaba un state viejo en session y Google decía "State not equal".
    Ahora limpiamos _google_authlib_state_ antes de ir a Google.
    """
    # Limpiamos sesión vieja antes de ir a Google
    session.pop("_google_authlib_state_", None)
    return google.authorize_redirect(
        url_for(
            "callback",
            _external=True,  # URL completa, porque Google tiene que volver
        )
    )

# ==============================================================================
# CALLBACK DE GOOGLE - CORRECCION 2
# ==============================================================================

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

    CORRECCION - Antes si fallaba el state, te tiraba 401 feo:
    "No se pudo completar el inicio de sesión"
    Ahora si es OAuthError (MismatchingStateError), hacemos session.clear()
    y te mandamos de nuevo a /login/google limpio. Reintentás y entra.
    """
    try:
        # Obtener y validar token
        token = google.authorize_access_token()
        # userinfo = datos que nos da Google: nombre, email, foto
        datos = token["userinfo"]
    except OAuthError:
        # ESTE ES EL ERROR DE TU FOTO: MismatchingStateError
        app.logger.exception("Error de state en Google - reintentando login")
        session.clear()
        return redirect(url_for("login_google"))
    except Exception:
        app.logger.exception(
            "Error durante el login con Google"
        )
        return (
            "No se pudo completar el inicio de sesión.",
            401,
        )

    # Si Google no nos dio email, no podemos crear usuario
    if not datos.get("email"):
        return ("Google no devolvió un email.", 401)

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # ------------------------------------------------
                # CORRECCION 2: NO USAMOS ON CONFLICT (email)
                # ------------------------------------------------
                # ANTES: INSERT ... ON CONFLICT (email) DO UPDATE
                # PROBLEMA: Si la columna email NO tiene UNIQUE
                # en tu base, Postgres tira error y el login
                # se rompe con 500. Por eso a veces no andaba Google.
                # AHORA: hacemos 1. Buscar, 2. Si existe actualizar,
                # 3. Si no existe crear. Asi anda siempre, tenga
                # o no tenga UNIQUE.
                # ------------------------------------------------
                # 1. Buscar por email
                cursor.execute(
                    """
                    SELECT
                        id,
                        rol,
                        activo
                    FROM usuarios
                    WHERE email = %s
                    """,
                    (datos["email"],),
                )
                fila = cursor.fetchone()

                if fila:
                    # Ya existe -> actualizamos nombre por si cambio en Google
                    usuario_id, rol, activo = fila
                    cursor.execute(
                        """
                        UPDATE usuarios
                        SET nombre = %s
                        WHERE id = %s
                        """,
                        (
                            datos.get("name", "Sin nombre"),
                            usuario_id,
                        ),
                    )
                else:
                    # No existe -> lo creamos como operador
                    # Los usuarios nuevos comienzan como operador.
                    # El admin después lo puede pasar a administrador en /usuarios.
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
                        RETURNING
                            id,
                            rol,
                            activo
                        """,
                        (
                            datos.get("name", "Sin nombre"),
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
        "nombre": datos.get("name", "Sin nombre"),
        "email": datos["email"],
        "rol": rol,
    }
    # Hacer la sesión permanente durante el tiempo configurado
    # por Flask (12 horas en PERMANENT_SESSION_LIFETIME).
    session.permanent = True
    return redirect("/")

# ==============================================================================
# USUARIOS
# ==============================================================================

@app.route("/usuarios")
@admin_required
def usuarios():
    """
    Lista de usuarios.

    SOLO administrador.
    Muestra id, nombre, email, rol, activo.
    Ordenado por id.
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
        return (
            "No se pudieron consultar los usuarios.",
            500,
        )

@app.route("/control")
def control_mqtt():
    return render_template("control_mqtt.html")


# BAJA DE USUARIO
# ==============================================================================

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

# ==============================================================================
# REACTIVAR USUARIO
# ==============================================================================

@app.route(
    "/usuarios/<int:id>/reactivar",
    methods=["POST"],
)
@admin_required
def reactivar_usuario(id):
    """
    Reactiva un usuario.
    Pone activo = TRUE de nuevo.
    Es lo contrario de baja.
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

# ==============================================================================
# CAMBIAR ROL
# ==============================================================================

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

# ==============================================================================
# ==============================================================================
# ETAPA 2: MIS ROBOTS + CÓDIGOS DE INVITACIÓN
# ==============================================================================
# ==============================================================================
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
#
# Tabla invitaciones (columnas):
#   id, codigo, robot_id, creado_por, fecha_creacion,
#   vence_en, usos_max, usos_actuales, activo
#
# Tabla robot_usuarios:
#   robot_id, usuario_id
# ==============================================================================

def generar_codigo_invitacion():
    """
    Genera un código tipo PROTUD-K7Q2.

    - PROTUD- = prefijo fijo, para que se entienda que es de Protud
    - K7Q2 = 4 caracteres aleatorios, sin letras confusas
      (sin O, 0, I, 1) para que no se confunda al dictarlo por WhatsApp.

    Ejemplo: PROTUD-K7Q2, PROTUD-X9M4, PROTUD-A8B3

    Alfabeto:
        ABCDEFGHJKLMNPQRSTUVWXYZ23456789
        Sin O porque se confunde con 0
        Sin I porque se confunde con 1
        Sin L porque se confunde con 1
        Sin 0 y 1 por lo mismo
    """
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

    Lógica de robots:
        - Admin: SELECT * FROM robots -> ve todos
        - Operador: JOIN robots + robot_usuarios WHERE usuario_id = mi id

    Lógica de invitaciones:
        - Solo admin ve sus códigos, LIMIT 20, los más nuevos primero.
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
    - Empieza con usos_actuales = 0, activo = TRUE
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

# CORRECCION 3: ANTES SOLO EXISTIA /unirse
# Si tu template usaba /mis-robots/unirse, daba 404 y no te dejaba unirte.
# AHORA: las 2 rutas van a la misma funcion. Andan las 2.
# @app.route("/unirse") + @app.route("/mis-robots/unirse") = mismo código, 2 URLs.
@app.route("/unirse", methods=["POST"])
@app.route("/mis-robots/unirse", methods=["POST"])
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

    CORRECCION: Antes si el código era inválido, te devolvía 404 en blanco.
    Ahora usa flash() + redirect a /mis-robots, para que veas el mensaje
    en la página y no te quede la pantalla blanca.

    CORRECCION: Antes comparaba vence_en (con zona horaria) con datetime.now()
    (sin zona) y Python tiraba TypeError y te daba 500 aunque el código
    no había vencido. Ahora le sacamos la zona con .replace(tzinfo=None)
    antes de comparar.
    """
    usuario = session["usuario"]
    # El código viene del form de Mis Robots
    # .upper() = si escribe protud-k7q2 en minúscula, igual anda
    # .strip() = saca espacios de más adelante y atrás
    codigo = (request.form.get("codigo") or "").strip().upper()

    if not codigo:
        flash("Escribí un código.", "error")
        return redirect(url_for("mis_robots"))

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
                    flash("Código inválido.", "error")
                    return redirect(url_for("mis_robots"))

                # Desarmamos la tupla en variables con nombre
                inv_id, robot_id, vence_en, usos_max, usos_actuales, activo = inv

                # ------------------------------------------------
                # 2. Validar: activo, no vencido, con usos libres
                # ------------------------------------------------
                # Si el admin lo revocó, activo = False
                if not activo:
                    flash("Este código fue revocado.", "error")
                    return redirect(url_for("mis_robots"))

                # Si la fecha de vencimiento ya pasó, no sirve
                # CORRECCION zona horaria: sacamos tzinfo si tiene
                if vence_en is not None:
                    vence_sin_zona = vence_en.replace(tzinfo=None) if vence_en.tzinfo else vence_en
                    if vence_sin_zona < datetime.now():
                        flash("Este código venció.", "error")
                        return redirect(url_for("mis_robots"))

                # Si ya lo usaron 5 veces, no quedan usos
                if usos_actuales >= usos_max:
                    flash("Este código ya se usó muchas veces.", "error")
                    return redirect(url_for("mis_robots"))

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
                    flash("Ya estás unido a ese robot.", "info")
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

        flash("¡Listo! Ya estás unido al robot.", "success")
        return redirect(url_for("mis_robots"))

    except psycopg.Error:
        app.logger.exception("Error al unirse con código")
        flash("No se pudo unir al robot.", "error")
        return redirect(url_for("mis_robots"))

@app.route("/invitaciones/<int:inv_id>/revocar", methods=["POST"])
@login_required
def revocar_invitacion(inv_id):
    """
    Revoca (anula) un código de invitación.

    Ejemplo: creaste PROTUD-K7Q2 y se filtró, lo revocás y ya nadie
    más lo puede usar, aunque no haya vencido.

    Revocar = poner activo = FALSE, no borrar la fila.
    Así queda registro de que existió.

    Permisos:
        - Admin: puede revocar cualquiera
        - Operador: solo los que creó él (creado_por = mi id)
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

# ==============================================================================
# CHAT
# ==============================================================================

LARGO_MAXIMO_MENSAJE = 500
# LARGO_MAXIMO_MENSAJE = ningún mensaje puede tener más de 500 letras.
# Así evitamos mensajes gigantes que rompan la base.
# Se usa en /chat, /api/chat/enviar.
# texto[:500] = corta el texto a 500 si viene más largo.

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

    Métodos:
        GET = muestra la página con mensajes
        POST = viejo, por compatibilidad. Guarda mensaje y hace redirect.
               El chat nuevo usa /api/chat/enviar con JS, sin recargar.
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
                # Los borrados tienen activo = FALSE y no se muestran,
                # pero siguen en la base por si hay que auditar.
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

# ==============================================================================
# API DEL CHAT EN VIVO
# ==============================================================================
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
#
# En chat.html el JS hace:
#   setInterval(() => fetch("/api/chat/mensajes?robot=1"), 2000)
#   fetch("/api/chat/enviar", {method: "POST", body: JSON.stringify({texto, robot})})

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
                "fecha": fecha.strftime("%H:%M") if fecha else "",
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

    Si el mensaje está vacío, devuelve 400.
    Si no tiene permiso, devuelve 403.
    """
    usuario = session["usuario"]
    # request.get_json() lee el JSON que mandó el JS
    datos = request.get_json() or {}
    # Limpiamos espacios y cortamos a 500 caracteres
    texto = (datos.get("texto") or "").strip()[:LARGO_MAXIMO_MENSAJE]
    # robot puede venir como string "1", lo convertimos a int con try
    try:
        robot_id = int(datos.get("robot", 1))
    except (TypeError, ValueError):
        return "Robot inválido.", 400
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

# ==============================================================================
# BORRAR MENSAJE
# ==============================================================================

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
    Así queda registro y se puede auditar después.
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

# ==============================================================================
# CIERRE DE SESIÓN
# ==============================================================================

@app.route("/logout")
def logout():
    """
    Cierra completamente la sesión actual.
    Borra todo lo que había en session.
    Después manda a la portada /.
    """
    session.clear()
    return redirect(
        url_for("inicio")
    )

# ==============================================================================
# WEBHOOK DE TELEGRAM - /webhook - CORRECCION 4
# ==============================================================================
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
#
# CORRECCION 4 - ANTES:
# Tu webhook solo entendía /start.
# Si mandabas /unirme PROTUD-K7Q2, no entraba en ningún if,
# no hacía nada, y vos veías que no pasaba nada o te decía
# "No pude cargar tus espacios" porque otro código viejo intentaba
# buscar en una tabla "espacios" que no existe.
#
# AHORA:
# Entiende /start, /unirme, /mis_espacios, /mis_robots, /ayuda
# Y siempre devuelve "ok" 200 para que Telegram no reintente 20 veces.
# ==============================================================================

# Leemos el token de las variables de entorno de Render.
# En Render tiene que estar: TELEGRAM_BOT_TOKEN
# En .env local también tiene que estar para probar.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Armamos la URL base de la API de Telegram con ese token
# Queda: https://api.telegram.org/bot123456:ABC-DEF...
# Si TELEGRAM_BOT_TOKEN es None, queda .../botNone, pero mandar_mensaje_telegram
# lo frena antes con if not TELEGRAM_BOT_TOKEN: return
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def mandar_mensaje_telegram(chat_id, texto):
    """
    Manda un mensaje de texto a un chat de Telegram.
    chat_id = a quién (el número que Telegram le da a cada persona)
    texto = qué le decimos

    Si no hay token, no podemos mandar nada, salimos sin romper.
    Si Telegram falla (sin internet, token malo), lo dejamos en print
    pero no rompemos la página. El webhook igual devuelve "ok".
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

def _guardar_suscriptor(chat_id, nombre):
    """
    Guarda o reactiva un suscriptor de Telegram.

    CORRECCION: NO USAMOS ON CONFLICT (chat_id)
    ANTES: INSERT ... ON CONFLICT (chat_id) DO UPDATE
    PROBLEMA: Si chat_id NO tiene UNIQUE en tu base,
    Postgres tira error y Telegram no guarda a nadie.
    AHORA: 1. Buscar por chat_id,
    2. Si existe actualizar nombre y reactivar,
    3. Si no existe crear.
    Asi Braian puede mandar /start 10 veces y no se duplica,
    y anda aunque no haya UNIQUE.

    Tabla suscriptores_telegram:
        id, chat_id (bigint), nombre, activo, fecha_creacion
    chat_id en la base es bigint, no text. Por eso hacemos int(chat_id).
    """
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT id
                FROM suscriptores_telegram
                WHERE chat_id = %s
                """,
                (int(chat_id),),  # int() porque en la base chat_id es bigint, no text
            )
            fila_existe = cursor.fetchone()
            if fila_existe:
                # Ya existe -> lo reactivamos y actualizamos nombre
                cursor.execute(
                    """
                    UPDATE suscriptores_telegram
                    SET nombre = %s, activo = TRUE
                    WHERE chat_id = %s
                    """,
                    (nombre, int(chat_id)),
                )
            else:
                # No existe -> lo creamos
                cursor.execute(
                    """
                    INSERT INTO suscriptores_telegram (chat_id, nombre, activo)
                    VALUES (%s, %s, TRUE)
                    """,
                    (int(chat_id), nombre),
                )

def _unirse_por_telegram(chat_id, codigo):
    """
    Une a una persona de Telegram a un robot usando un código PROTUD-XXXX.
    Devuelve un texto para mandarle de vuelta por Telegram.

    ESTA ES LA FUNCIÓN QUE FALTABA ANTES y por eso /unirme te decía
    "No pude cargar tus espacios".

    Pasos:
        1. Limpiar código: upper + strip
        2. Buscar código en invitaciones
        3. Validar: existe, activo, no vencido, con usos libres
        4. Buscar nombre del robot para mensaje lindo
        5. Intentar guardar en telegram_robot_usuarios (si existe la tabla)
        6. Sumar 1 uso al código
        7. Devolver mensaje de éxito

    Si la tabla telegram_robot_usuarios no existe en tu base,
    NO ROMPE: hace rollback de ese intento y sigue con el resto.
    Por eso tenés que crear esa tabla con este SQL (1 sola vez en Render):
        CREATE TABLE IF NOT EXISTS telegram_robot_usuarios (
            chat_id BIGINT NOT NULL,
            robot_id INTEGER NOT NULL,
            PRIMARY KEY (chat_id, robot_id)
        );

    Si no querés crearla, igual el código se marca como usado,
    pero /mis_espacios no va a poder listar. Por eso mejor crearla.
    """
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return "Escribí el código así: /unirme PROTUD-K7Q2"
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # 1. Buscar código
                cursor.execute(
                    """
                    SELECT id, robot_id, vence_en, usos_max, usos_actuales, activo
                    FROM invitaciones WHERE codigo = %s
                    """,
                    (codigo,),
                )
                inv = cursor.fetchone()
                if not inv:
                    return "❌ Código inválido. Fijate que lo copiaste bien: /unirme PROTUD-K7Q2"

                inv_id, robot_id, vence_en, usos_max, usos_actuales, activo = inv

                if not activo:
                    return "❌ Este código fue revocado por el admin."

                # CORRECCION zona horaria: sacamos tzinfo antes de comparar
                if vence_en is not None:
                    vence_sin_zona = vence_en.replace(tzinfo=None) if vence_en.tzinfo else vence_en
                    if vence_sin_zona < datetime.now():
                        return "❌ Este código venció. Pedile uno nuevo al admin."

                if usos_actuales >= usos_max:
                    return "❌ Este código ya se usó muchas veces."

                # 2. Buscar nombre del robot para el mensaje lindo
                cursor.execute("SELECT nombre FROM robots WHERE id = %s", (robot_id,))
                fila_robot = cursor.fetchone()
                nombre_robot = fila_robot[0] if fila_robot else f"Robot {robot_id}"

                # 3. ¿Ya está unido?
                try:
                    cursor.execute(
                        """
                        SELECT 1 FROM telegram_robot_usuarios
                        WHERE chat_id = %s AND robot_id = %s
                        """,
                        (int(chat_id), robot_id),
                    )
                    if cursor.fetchone():
                        return f"✅ Ya estás unido a {nombre_robot}."
                    cursor.execute(
                        "INSERT INTO telegram_robot_usuarios (chat_id, robot_id) VALUES (%s, %s)",
                        (int(chat_id), robot_id),
                    )
                except psycopg.Error:
                    # Si no existe la tabla telegram_robot_usuarios, no rompemos.
                    # Hacemos rollback solo de este intento y seguimos con el uso del código.
                    conexion.rollback()
                    pass

                # 4. Sumar 1 uso al código
                # OJO: después del rollback, tenemos que abrir de nuevo la transacción.
                # psycopg con with la reabre sola en el próximo execute.
                cursor.execute(
                    "UPDATE invitaciones SET usos_actuales = usos_actuales + 1 WHERE id = %s",
                    (inv_id,),
                )

                return f"✅ ¡Listo! Ya estás unido a {nombre_robot}.\nAhora vas a recibir sus alertas acá en Telegram."
    except psycopg.Error:
        app.logger.exception("Error al unirse por Telegram")
        return "❌ No pude unirte, hubo un error en la base. Probá de nuevo en 1 minuto."

def _mis_espacios_telegram(chat_id):
    """
    Devuelve el texto con los robots a los que está unido este chat de Telegram.

    Lee de telegram_robot_usuarios JOIN robots.
    Si no hay filas, dice que todavía no está unido y le explica cómo unirse.
    Si no existe la tabla, atrapa el error y devuelve el mismo mensaje,
    no rompe el webhook.

    Ejemplo de salida:
        🤖 Tus robots:
        • Mini Protud
        • Robot Pasillo
    """
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT r.nombre
                    FROM telegram_robot_usuarios AS tru
                    JOIN robots AS r ON r.id = tru.robot_id
                    WHERE tru.chat_id = %s
                    ORDER BY r.nombre
                    """,
                    (int(chat_id),),
                )
                filas = cursor.fetchall()
                if not filas:
                    return "Todavía no estás unido a ningún robot.\nPedile un código al admin y mandá: /unirme PROTUD-K7Q2"
                nombres = "\n".join([f"• {f[0]}" for f in filas])
                return f"🤖 Tus robots:\n{nombres}"
    except psycopg.Error:
        # Si no existe la tabla, no rompemos, le explicamos cómo unirse
        return "Todavía no estás unido a ningún robot.\nPedile un código al admin y mandá: /unirme PROTUD-K7Q2"

@app.route("/webhook", methods=["POST"])
def webhook_telegram():
    """
    Recibe los mensajes que Telegram nos manda.
    Cuando alguien manda /start, lo suscribimos.
    Cuando manda /unirme, lo unimos.
    Cuando manda /mis_espacios, le listamos sus robots.

    Formato que manda Telegram:
    {
      "message": {
        "text": "/start",
        "chat": {"id": 123456, "first_name": "Ariel", "last_name": "", "username": "ariel"},
        ...
      }
    }

    Siempre devolvemos "ok", 200 para que Telegram no reintente.
    Si devolvemos 500, Telegram reintenta 20 veces y te spamea.
    Por eso el try gigante: aunque falle la base, devolvemos "ok".
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

        # Si no hay chat_id o texto, no hacemos nada
        if not chat_id or not texto:
            return "ok", 200

        # /start -> suscribir
        if texto == "/start":
            _guardar_suscriptor(chat_id, nombre)
            print(f"GUARDADO WEBHOOK: {chat_id} - {nombre}")
            mandar_mensaje_telegram(
                chat_id,
                "✅ ¡Listo! Ya estás suscripto a las alertas de PROTUD.\n\nPara unirte a un robot mandá:\n/unirme PROTUD-K7Q2\n\nPara ver tus robots mandá:\n/mis_espacios"
            )
            return "ok", 200

        # /unirme CODIGO -> unir a robot
        if texto.startswith("/unirme"):
            partes = texto.split()
            if len(partes) < 2:
                mandar_mensaje_telegram(chat_id, "Escribí así: /unirme PROTUD-K7Q2")
            else:
                try:
                    _guardar_suscriptor(chat_id, nombre)
                except Exception:
                    pass
                respuesta = _unirse_por_telegram(chat_id, partes[1])
                mandar_mensaje_telegram(chat_id, respuesta)
            return "ok", 200

        # /mis_espacios o /mis_robots -> ver robots
        if texto in ("/mis_espacios", "/mis_robots", "/misrobots"):
            respuesta = _mis_espacios_telegram(chat_id)
            mandar_mensaje_telegram(chat_id, respuesta)
            return "ok", 200

        # /ayuda -> ayuda
        if texto in ("/ayuda", "/help", "/ayuda"):
            mandar_mensaje_telegram(
                chat_id,
                "🤖 Ayuda PROTUD\n\n/start - Suscribirte a alertas\n/unirme PROTUD-K7Q2 - Unirte a un robot con código\n/mis_espacios - Ver tus robots"
            )
            return "ok", 200

        # Si mandó cualquier otra cosa, le respondemos ayuda corta
        mandar_mensaje_telegram(
            chat_id,
            "No te entendí 😅\nMandá /ayuda para ver los comandos."
        )
        return "ok", 200

    except Exception as e:
        # Si algo falla, lo mostramos en los logs de Render
        # y igual devolvemos "ok" para que Telegram no nos spamee
        print(f"Error webhook: {e}")
        return "ok", 200

# ==============================================================================
# INICIAR SERVIDOR
# ==============================================================================

if __name__ == "__main__":
    # Para desarrollo local.
    #
    # IMPORTANTE:
    # debug=True NO debe utilizarse en producción.
    # En producción, Render corre la app con gunicorn.
    # gunicorn no usa este if, usa directamente app = Flask(...)
    # Por eso acá solo ponemos app.run para cuando hacés python app.py
    # en tu compu.
    app.run(debug=True)