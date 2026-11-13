import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg

load_dotenv(Path(__file__).parent / ".env")

url = os.getenv("DATABASE_URL")
if url:
    conn = psycopg.connect(url)
else:
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

with conn.cursor() as cur:
    cur.execute("SELECT * FROM suscriptores_telegram;")
    print(cur.fetchall())