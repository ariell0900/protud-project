"""
PROTUD - Aplicación web (Flask)

Página web del robot de vigilancia Protud. Desde acá se:
- inicia sesión con Google,
- ven las alertas, fotos y notificaciones del robot,
- administran los usuarios (con baja lógica),
- usa el Sistema de Chat, donde el equipo de cada robot se organiza.

Datos: PostgreSQL (en la compu usa el .env; en Render usa DATABASE_URL).
Avisos: Telegram (ver telegram_service.py).
"""

# ---------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------
import os                      # Leer variables de entorno (claves del .env)
from pathlib import Path       # Armar rutas de archivos que funcionan en Windows y Linux
from html import escape        # Escapar texto HTML (por ahora no se usa)

# Funciones propias para mandar avisos y fotos por Telegram
from telegram_service import enviar_alerta_telegram, enviar_foto_telegram

# Authlib: maneja el inicio de sesión con Google (OAuth2 / OpenID)
from authlib.integrations.flask_client import OAuth

import psycopg                 # Conexión con PostgreSQL
from dotenv import load_dotenv # Carga el archivo .env

# Flask: el framework web
# - render_template: muestra un HTML de la carpeta templates
# - redirect / url_for: mandan al usuario a otra página
# - session: guarda quién inició sesión
# - request: lee lo que manda un formulario o la URL
from flask import Flask, render_template, redirect, url_for, session, request


# ---------------------------------------------------------------
# Configuración inicial
# ---------------------------------------------------------------

# Cargar las variables privadas de configuración (.env está en la misma carpeta)
load_dotenv(Path(__file__).resolve().parent / ".env")

# Crear la aplicación Flask
app = Flask(__name__)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Clave secreta: Flask la usa para firmar la sesión y que nadie la falsifique
app.secret_key = os.getenv("SECRET_KEY")

# Login con Google: le presentamos Protud a Google con las claves del .env
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ---------------------------------------------------------------
# Conexión a PostgreSQL
# ---------------------------------------------------------------
def conectar_db():
    """Devuelve una conexión abierta a la base de datos protud."""
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
# Páginas principales
# ---------------------------------------------------------------

# Portada de Protud
@app.route("/")
def inicio():
    return render_template("index.html")


# Panel: resumen con números reales de la base
@app.route("/panel")
def panel():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # Cuenta: alertas pendientes, alertas de las últimas 24 h y fotos
                cursor.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE NOT atendida),
                        COUNT(*) FILTER (WHERE fecha_hora >= NOW() - INTERVAL '24 hours'),
                        COUNT(foto_url)
                    FROM alertas
                """)
                pendientes, ultimas_24h, imagenes = cursor.fetchone()

                # Las 5 alertas más nuevas para la tabla del panel
                cursor.execute("""
                    SELECT fecha_hora, tipo, atendida
                    FROM alertas
                    ORDER BY fecha_hora DESC
                    LIMIT 5
                """)
                ultimas = cursor.fetchall()

        return render_template(
            "panel.html",
            pendientes=pendientes,
            ultimas_24h=ultimas_24h,
            imagenes=imagenes,
            ultimas=ultimas
        )

    except psycopg.Error:
        app.logger.exception("Error al cargar el panel")
        return "No se pudo cargar el panel.", 500


# Página del robot: muestra la última alerta
@app.route("/robot")
def robot():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT tipo, descripcion, fecha_hora, atendida
                    FROM alertas
                    ORDER BY fecha_hora DESC
                    LIMIT 1
                """)
                ultima = cursor.fetchone()

        return render_template("robot.html", ultima=ultima)

    except psycopg.Error:
        app.logger.exception("Error al cargar el robot")
        return "No se pudo cargar la página del robot.", 500


# Página de control del robot (botones de manejo)
@app.route("/control")
def control():
    return render_template("control.html")


# Fotos tomadas por el robot
@app.route("/fotos")
def fotos():
    # Fotos de ejemplo: más adelante las traemos de PostgreSQL
    lista = [
        {"archivo": "robot.jpg", "motivo": "Movimiento detectado", "fecha": "18/10/2026 03:15"},
        {"archivo": "robot.jpg", "motivo": "Obstáculo en el pasillo", "fecha": "17/10/2026 22:40"},
        {"archivo": "robot.jpg", "motivo": "Patrulla de prueba", "fecha": "17/10/2026 20:05"},
    ]
    return render_template("fotos.html", fotos=lista)


# Comprobar la conexión con PostgreSQL
@app.route("/probar-db")
def probar_db():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM robots")
                cantidad = cursor.fetchone()[0]

        return (
            f"PROTUD conectado a PostgreSQL. "
            f"Robots registrados: {cantidad}"
        )

    except psycopg.Error:
        app.logger.exception("Error al conectar con PostgreSQL")
        return "No se pudo conectar con PostgreSQL. Revisá la terminal.", 500


# ---------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------

# Mostrar las alertas registradas, con el nombre del robot
@app.route("/alertas")
def ver_alertas():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
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
                """)

                alertas = cursor.fetchall()

        return render_template("alertas.html", alertas=alertas)

    except psycopg.Error:
        app.logger.exception("Error al consultar alertas")
        return "No se pudieron consultar las alertas.", 500


# Marcar una alerta como atendida
@app.route("/alertas/<int:alerta_id>/atender", methods=["POST"])
def atender_alerta(alerta_id):
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE alertas
                    SET atendida = TRUE
                    WHERE id = %s
                    """,
                    (alerta_id,)
                )

        return redirect(url_for("ver_alertas"))

    except psycopg.Error:
        app.logger.exception("Error al actualizar la alerta")
        return "No se pudo actualizar la alerta.", 500


# Volver una alerta a pendiente (deshacer)
@app.route("/alertas/<int:alerta_id>/deshacer", methods=["POST"])
def deshacer_alerta(alerta_id):
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE alertas
                    SET atendida = FALSE
                    WHERE id = %s
                    """,
                    (alerta_id,)
                )

        return redirect(url_for("ver_alertas"))

    except psycopg.Error:
        app.logger.exception("Error al deshacer la alerta")
        return "No se pudo deshacer la alerta.", 500


# ---------------------------------------------------------------
# Notificaciones (Telegram)
# ---------------------------------------------------------------

# Consultar las notificaciones registradas
@app.route("/notificaciones")
def ver_notificaciones():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        n.id,
                        n.mensaje,
                        n.fecha_envio,
                        n.leida,
                        n.alerta_id,
                        n.estado_envio
                    FROM notificaciones AS n
                    ORDER BY n.fecha_envio DESC
                """)
                notificaciones = cursor.fetchall()

        return render_template(
            "notificaciones.html",
            notificaciones=notificaciones
        )

    except psycopg.Error:
        app.logger.exception("Error al consultar notificaciones")
        return "No se pudieron consultar las notificaciones.", 500


# Prueba de integración Flask + Telegram
@app.route("/probar-telegram")
def probar_telegram_flask():
    enviado = enviar_alerta_telegram(
        robot="Mini Protud",
        evento="Movimiento detectado (SIMULACIÓN)",
        ubicacion="Escuela"
    )

    if enviado:
        return "PROTUD: Notificación enviada correctamente a Telegram."

    return "PROTUD: No se pudo enviar la notificación.", 500


# Guardar el resultado del envío a Telegram (enviada o fallida)
def registrar_notificacion(alerta_id, mensaje, enviado):
    estado = "enviada" if enviado else "fallida"

    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notificaciones
                    (alerta_id, mensaje, estado_envio)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (alerta_id, mensaje, estado)
            )
            return cursor.fetchone()[0]


# Registrar una alerta simulada y notificar por Telegram
@app.route("/simular-alerta", methods=["POST"])
def simular_alerta():
    try:
        # 1) Guardar la alerta en PostgreSQL
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO alertas
                        (robot_id, tipo, descripcion)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        1,
                        "movimiento",
                        "Mini Protud detectó movimiento (SIMULACIÓN)"
                    )
                )
                alerta_id = cursor.fetchone()[0]

        # 2) Mandar la foto de prueba por Telegram
        enviado = enviar_foto_telegram(
            robot="Mini Protud",
            evento="Movimiento detectado (SIMULACIÓN)",
            ubicacion="Escuela",
            ruta_foto=Path(__file__).resolve().parent / "static" / "prueba.jpeg"
        )

        # 3) Anotar si el envío salió bien o mal
        mensaje = "Mini Protud detectó movimiento (SIMULACIÓN)"

        notificacion_id = registrar_notificacion(
            alerta_id,
            mensaje,
            enviado
        )

        return {
            "alerta_id": alerta_id,
            "registrada": True,
            "telegram_enviado": enviado
        }, 201

    except psycopg.Error:
        app.logger.exception("Error al registrar la alerta")
        return {"error": "No se pudo registrar la alerta"}, 500


# ---------------------------------------------------------------
# Inicio de sesión con Google
# ---------------------------------------------------------------

# Manda al usuario a la página de Google para iniciar sesión
@app.route("/login/google")
def login_google():
    return google.authorize_redirect(url_for("callback", _external=True))


# Vuelta desde Google: anotamos quién inició sesión
@app.route("/callback")
def callback():
    token = google.authorize_access_token()
    datos = token["userinfo"]  # Nombre y email que nos da Google

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                # Si el usuario es nuevo, se crea como operador.
                # Si ya existía, solo se actualiza el nombre.
                cursor.execute(
                    """
                    INSERT INTO usuarios (nombre, email, rol)
                    VALUES (%s, %s, 'operador')
                    ON CONFLICT (email) DO UPDATE SET nombre = EXCLUDED.nombre
                    RETURNING id, rol, activo
                    """,
                    (datos["name"], datos["email"])
                )
                usuario_id, rol, activo = cursor.fetchone()

    except psycopg.Error:
        app.logger.exception("Error al guardar el usuario")
        return "No se pudo iniciar sesión.", 500

    # Baja lógica: un usuario inactivo no puede entrar
    if not activo:
        return "Tu cuenta está dada de baja.", 403

    # Guardar en la sesión quién está conectado
    session["usuario"] = {
        "id": usuario_id,
        "nombre": datos["name"],
        "email": datos["email"],
        "rol": rol,
    }
    return redirect(url_for("panel"))


# ---------------------------------------------------------------
# Usuarios (solo administrador)
# ---------------------------------------------------------------

# Lista de usuarios
@app.route("/usuarios")
def usuarios():
    if session.get("usuario", {}).get("rol") != "administrador":
        return "No tenés permiso.", 403
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT id, nombre, email, rol, activo FROM usuarios ORDER BY id")
            lista = cursor.fetchall()
    return render_template("usuarios.html", usuarios=lista)


# Baja lógica: no borra, solo marca inactivo
@app.route("/usuarios/<int:id>/baja", methods=["POST"])
def baja_usuario(id):
    if session.get("usuario", {}).get("rol") != "administrador":
        return "No tenés permiso.", 403
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET activo = FALSE WHERE id = %s", (id,))
    return redirect(url_for("usuarios"))


# Reactivar usuario
@app.route("/usuarios/<int:id>/reactivar", methods=["POST"])
def reactivar_usuario(id):
    if session.get("usuario", {}).get("rol") != "administrador":
        return "No tenés permiso.", 403
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("UPDATE usuarios SET activo = TRUE WHERE id = %s", (id,))
    return redirect(url_for("usuarios"))


# ---------------------------------------------------------------
# Sistema de Chat (NUEVO)
# Cada robot tiene su propio chat: el equipo que lo vigila
# se organiza ahí (ej: "vi la alerta, voy al pasillo 2").
# Los mensajes se guardan en la tabla "mensajes" (ver db/chat.sql).
# ---------------------------------------------------------------

LARGO_MAXIMO_MENSAJE = 500  # Para que nadie mande textos gigantes


@app.route("/chat", methods=["GET", "POST"])
def chat():
    # Solo pueden usar el chat los que iniciaron sesión
    usuario = session.get("usuario")
    if not usuario:
        return redirect(url_for("login_google"))

    # ¿De qué robot es el chat? Viene en la URL: /chat?robot=1
    # Si no viene, se usa el robot 1
    robot_id = request.values.get("robot", 1, type=int)

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:

                # POST = alguien tocó "Enviar": guardamos el mensaje
                if request.method == "POST":
                    texto = request.form.get("texto", "").strip()
                    if texto:
                        cursor.execute(
                            """
                            INSERT INTO mensajes (robot_id, usuario_id, texto)
                            VALUES (%s, %s, %s)
                            """,
                            (robot_id, usuario["id"], texto[:LARGO_MAXIMO_MENSAJE])
                        )
                    # Volvemos a la misma página (así no se reenvía al recargar)
                    return redirect(url_for("chat", robot=robot_id))

                # GET = mostrar el chat
                # Lista de robots para elegir de cuál ver el chat
                cursor.execute("SELECT id, nombre FROM robots ORDER BY id")
                robots = cursor.fetchall()

                # Mensajes activos de este robot, del más viejo al más nuevo
                cursor.execute(
                    """
                    SELECT m.id, m.texto, m.fecha, u.nombre, m.usuario_id
                    FROM mensajes AS m
                    JOIN usuarios AS u ON m.usuario_id = u.id
                    WHERE m.robot_id = %s AND m.activo
                    ORDER BY m.fecha ASC
                    """,
                    (robot_id,)
                )
                mensajes = cursor.fetchall()

        return render_template(
            "chat.html",
            robots=robots,
            robot_id=robot_id,
            mensajes=mensajes,
            usuario=usuario
        )

    except psycopg.Error:
        app.logger.exception("Error en el chat")
        return "No se pudo cargar el chat.", 500


# Baja lógica de un mensaje: no se borra, se oculta (activo = FALSE).
# Lo puede borrar quien lo escribió o un administrador.
@app.route("/chat/mensajes/<int:mensaje_id>/borrar", methods=["POST"])
def borrar_mensaje(mensaje_id):
    usuario = session.get("usuario")
    if not usuario:
        return redirect(url_for("login_google"))

    robot_id = request.form.get("robot", 1, type=int)

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                if usuario["rol"] == "administrador":
                    cursor.execute(
                        "UPDATE mensajes SET activo = FALSE WHERE id = %s",
                        (mensaje_id,)
                    )
                else:
                    # Un operador solo puede borrar sus propios mensajes
                    cursor.execute(
                        """
                        UPDATE mensajes SET activo = FALSE
                        WHERE id = %s AND usuario_id = %s
                        """,
                        (mensaje_id, usuario["id"])
                    )

        return redirect(url_for("chat", robot=robot_id))

    except psycopg.Error:
        app.logger.exception("Error al borrar el mensaje")
        return "No se pudo borrar el mensaje.", 500


# ---------------------------------------------------------------
# Iniciar el servidor Flask
# ---------------------------------------------------------------
if __name__ == "__main__":
    # debug=True solo para probar en la compu; sacarlo antes de publicar
    app.run(debug=True)