import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from flask import Flask

# Leer la configuración privada
load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)

@app.route("/")
def inicio():
    return "<h1>PROTUD - Sistema de Vigilancia</h1><p>Servidor funcionando correctamente.</p>"

@app.route("/probar-db")
def probar_db():
    try:
        with psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connect_timeout=5
        ) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM robots")
                cantidad = cursor.fetchone()[0]

        return f"PROTUD conectado a PostgreSQL. Robots registrados: {cantidad}"

    except psycopg.Error:
        app.logger.exception("Error al conectar con PostgreSQL")
        return "No se pudo conectar con PostgreSQL. Revisá la terminal.", 500

if __name__ == "__main__":
    app.run(debug=True)

