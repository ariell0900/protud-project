import os
from pathlib import Path
from html import escape
from telegram_service import enviar_alerta_telegram, enviar_foto_telegram
from authlib.integrations.flask_client import OAuth
 
import psycopg
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session
 
# Cargar las variables privadas de configuración
load_dotenv(Path(__file__).resolve().parent / ".env")
 
app = Flask(__name__)
 
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
 
 
# Conexión a PostgreSQL
def conectar_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5
    )
 
 
# Página principal
@app.route("/")
def inicio():
    return render_template("index.html")
 
 
# Panel: resumen con números reales
@app.route("/panel")
def panel():
    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE NOT atendida),
                        COUNT(*) FILTER (WHERE fecha_hora >= NOW() - INTERVAL '24 hours'),
                        COUNT(foto_url)
                    FROM alertas
                """)
                pendientes, ultimas_24h, imagenes = cursor.fetchone()
 
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
 
 
@app.route("/control")
def control():
    return render_template("control.html")
 
 
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
 
 
# Mostrar las alertas registradas
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
                        n.alerta_id
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
 
 
# Guardar el resultado del envío a Telegram
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
 
        # La alerta ya quedó guardada en PostgreSQL
        enviado = enviar_foto_telegram(
            robot="Mini Protud",
            evento="Movimiento detectado (SIMULACIÓN)",
            ubicacion="Escuela",
            ruta_foto=Path(__file__).resolve().parent / "static" / "prueba.jpeg"
        )
 
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
 
 
# Login con Google: manda al usuario a la página de Google
@app.route("/login/google")
def login_google():
    return google.authorize_redirect(url_for("callback", _external=True))
 
 
# Vu
# Vuelta desde Google: anotamos quién inició sesión
@app.route("/callback")
def callback():
    token = google.authorize_access_token()
    datos = token["userinfo"]

    try:
        with conectar_db() as conexion:
            with conexion.cursor() as cursor:
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

    if not activo:
        return "Tu cuenta está dada de baja.", 403

    session["usuario"] = {
        "id": usuario_id,
        "nombre": datos["name"],
        "email": datos["email"],
        "rol": rol,
    }
    return redirect(url_for("panel"))
 
 
# Iniciar el servidor Flask
if __name__ == "__main__":
    app.run(debug=True)
 