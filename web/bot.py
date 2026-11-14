# bot.py - Bot de Telegram de PROTUD v2
# Ahora con espacios privados, código de 24hs y aprobación del admin.
import os
import random
import string
from pathlib import Path
from datetime import datetime, timedelta, timezone
import psycopg
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

def conectar_db():
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg.connect(url, connect_timeout=5)
    return psycopg.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=5
    )

def mandar(chat_id, texto, botones=None):
    # botones: lista de botones inline de Telegram
    data = {"chat_id": chat_id, "text": texto}
    if botones:
        data["reply_markup"] = {"inline_keyboard": botones}
    requests.post(f"{API}/sendMessage", json=data, timeout=10)

def generar_codigo():
    return ''.join(random.choices(string.digits, k=6))

def generar_id_robot():
    return "PROTUD-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- Memoria temporal: en qué paso está cada usuario ---
# Ej: estados[chat_id] = "esperando_nombre_espacio" o "esperando_codigo"
estados = {}

def escuchar():
    offset = 0
    print("Bot PROTUD v2 escuchando... espacios + códigos + admin")
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35).json()
        except:
            continue

        for update in r.get("result", []):
            offset = update["update_id"] + 1

            # 1. BOTONES que apretó alguien (Aceptar / Rechazar / Crear / Unirse)
            if "callback_query" in update:
                cb = update["callback_query"]
                chat_id = cb["from"]["id"]
                data = cb.get("data", "")
                # Le sacamos el "cargando..." al botón
                requests.post(f"{API}/answerCallbackQuery", json={"callback_query_id": cb["id"]}, timeout=10)

                if data == "crear":
                    estados[chat_id] = "esperando_nombre_espacio"
                    mandar(chat_id, "¿Cómo se llama tu espacio? Ej: Escuela 1")
                elif data == "unirse":
                    estados[chat_id] = "esperando_codigo"
                    mandar(chat_id, "Pasame el código de 6 números que te compartió tu admin.")
                elif data.startswith("aceptar_"):
                    pedido_id = int(data.split("_")[1])
                    aceptar_pedido(pedido_id)
                elif data.startswith("rechazar_"):
                    pedido_id = int(data.split("_")[1])
                    rechazar_pedido(pedido_id)
                continue

            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            texto = msg.get("text", "").strip()
            nombre = msg["from"].get("first_name", "")
            username = msg["from"].get("username", "")

            # /start: menú principal
            if texto == "/start":
                estados.pop(chat_id, None)
                mandar(chat_id,
                    "👋 Bienvenido a PROTUD\n\n¿Qué querés hacer?",
                    botones=[
                        [{"text": "➕ Crear espacio nuevo", "callback_data": "crear"}],
                        [{"text": "🔑 Unirme con código", "callback_data": "unirse"}]
                    ])
                continue

            # Si está esperando el nombre del espacio -> lo crea
            if estados.get(chat_id) == "esperando_nombre_espacio":
                crear_espacio(chat_id, nombre, username, texto)
                estados.pop(chat_id, None)
                continue

            # Si está esperando el código -> intenta unirse
            if estados.get(chat_id) == "esperando_codigo":
                intentar_unirse(chat_id, nombre, username, texto)
                estados.pop(chat_id, None)
                continue

            if texto == "/stop":
                with conectar_db() as c:
                    with c.cursor() as cur:
                        cur.execute("UPDATE miembros_espacio SET activo=FALSE WHERE chat_id=%s", (chat_id,))
                mandar(chat_id, "Te diste de baja de las alertas.")
                continue

def crear_espacio(chat_id, nombre, username, nombre_espacio):
    codigo = generar_codigo()
    id_robot = generar_id_robot()
    vence = datetime.now(timezone.utc) + timedelta(hours=24)
    with conectar_db() as c:
        with c.cursor() as cur:
            cur.execute("INSERT INTO espacios (nombre, admin_chat_id) VALUES (%s,%s) RETURNING id", (nombre_espacio, chat_id))
            espacio_id = cur.fetchone()[0]
            cur.execute("INSERT INTO robots (espacio_id, codigo_robot, nombre) VALUES (%s,%s,%s)", (espacio_id, id_robot, f"Robot de {nombre_espacio}"))
            cur.execute("INSERT INTO miembros_espacio (espacio_id, chat_id, nombre, username, rol) VALUES (%s,%s,%s,%s,'admin')", (espacio_id, chat_id, nombre, username))
            cur.execute("INSERT INTO codigos_invitacion (espacio_id, codigo, vence_en) VALUES (%s,%s,%s)", (espacio_id, codigo, vence))
    mandar(chat_id, f"✅ ¡Espacio creado!\n\n🏫 Espacio: {nombre_espacio}\n🤖 Robot ID: {id_robot} (no cambia nunca)\n🔑 Tu código para invitar (dura 24hs): {codigo}\n\nCompartí ese código con tus compañeros. Cuando quieran entrar, te voy a avisar para que los aceptes o rechaces.")

def intentar_unirse(chat_id, nombre, username, codigo):
    with conectar_db() as c:
        with c.cursor() as cur:
            cur.execute("""
                SELECT e.id, e.nombre, e.admin_chat_id FROM codigos_invitacion ci
                JOIN espacios e ON e.id = ci.espacio_id
                WHERE ci.codigo=%s AND ci.vence_en > NOW() AND ci.usado=FALSE
            """, (codigo,))
            fila = cur.fetchone()
            if not fila:
                mandar(chat_id, "❌ Ese código no existe o ya venció. Pedile uno nuevo a tu admin.")
                return
            espacio_id, nombre_espacio, admin_chat_id = fila
            # Guardamos el pedido pendiente
            cur.execute("INSERT INTO pedidos_union (espacio_id, chat_id, nombre, username) VALUES (%s,%s,%s,%s) RETURNING id", (espacio_id, chat_id, nombre, username))
            pedido_id = cur.fetchone()[0]
    mandar(chat_id, f"⏳ Pedido enviado a {nombre_espacio}. Esperá que el admin te acepte.")
    # Aviso al admin con botones
    mandar(admin_chat_id,
        f"🔔 Alguien quiere unirse a tu espacio {nombre_espacio}\n\n👤 {nombre} (@{username})\n\n¿Qué hacés?",
        botones=[
            [{"text": "✅ Aceptar", "callback_data": f"aceptar_{pedido_id}"}, {"text": "❌ Rechazar", "callback_data": f"rechazar_{pedido_id}"}]
        ])

def aceptar_pedido(pedido_id):
    with conectar_db() as c:
        with c.cursor() as cur:
            cur.execute("SELECT espacio_id, chat_id, nombre, username FROM pedidos_union WHERE id=%s AND estado='pendiente'", (pedido_id,))
            p = cur.fetchone()
            if not p: return
            espacio_id, chat_id, nombre, username = p
            cur.execute("UPDATE pedidos_union SET estado='aceptado' WHERE id=%s", (pedido_id,))
            cur.execute("INSERT INTO miembros_espacio (espacio_id, chat_id, nombre, username, rol) VALUES (%s,%s,%s,%s,'miembro') ON CONFLICT (espacio_id, chat_id) DO UPDATE SET activo=TRUE", (espacio_id, chat_id, nombre, username))
            cur.execute("SELECT nombre FROM espacios WHERE id=%s", (espacio_id,))
            nombre_espacio = cur.fetchone()[0]
    mandar(chat_id, f"✅ ¡Aceptado! Ya estás en {nombre_espacio}. Ahora te van a llegar sus alertas acá y podés entrar al chat en la web.")
    mandar(chat_id, "Ya podés entrar a la web con tu cuenta y vas a ver el chat de tu espacio.")

def rechazar_pedido(pedido_id):
    with conectar_db() as c:
        with c.cursor() as cur:
            cur.execute("SELECT chat_id FROM pedidos_union WHERE id=%s", (pedido_id,))
            fila = cur.fetchone()
            if not fila: return
            cur.execute("UPDATE pedidos_union SET estado='rechazado' WHERE id=%s", (pedido_id,))
    mandar(fila[0], "❌ El admin rechazó tu pedido para unirte al espacio.")

if __name__ == "__main__":
    escuchar()