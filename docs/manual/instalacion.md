# Instalación

## Requisitos previos

Antes de instalar necesitás:

- Python 3.11 o superior
- PostgreSQL (en local o en Render)
- Cuenta de Google Cloud para OAuth
- Bot de Telegram creado con BotFather
- Cuenta en GitLab y en Render
- Git instalado

## 1. Clonar el repositorio

```bash
git clone https://gitlab.com/TU-USUARIO/protud.git
cd protud
```

## 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv
```

En Windows:

```bash
venv\Scripts\activate
```

En Linux / Mac:

```bash
source venv/bin/activate
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:

- Flask: framework web
- gunicorn: servidor para producción en Render
- psycopg2-binary: conexión a PostgreSQL
- google-auth: verificación del token de Google
- requests: llamadas a la API de Telegram
- python-dotenv: leer variables del archivo .env

## 4. Crear archivo .env

En la raíz del proyecto, al lado de `app.py`, creá un archivo que se llame `.env`:

```env
SECRET_KEY=tu_clave_secreta_larga_y_aleatoria
GOOGLE_CLIENT_ID=tu_client_id_google.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_client_secret_google
DATABASE_URL=postgresql://usuario:contraseña@host:5432/protud
TELEGRAM_BOT_TOKEN=tu_token_telegram_de_botfather
SESSION_COOKIE_SECURE=false
```

**Importante:**

- En local: `SESSION_COOKIE_SECURE=false`
- En Render: `SESSION_COOKIE_SECURE=true`
- Nunca subas el `.env` a GitLab. Tiene que estar en `.gitignore`.

## 5. Crear la base de datos

### En Render

1. Entrá a Render > New > PostgreSQL
2. Creá la base
3. Copiá la `DATABASE_URL` que te da Render
4. Pegala en el `.env` y en las variables de entorno de Render

### Tablas

La base de producción ya tiene las tablas principales: usuarios, robots, robot_usuarios, invitaciones, alertas, notificaciones, mensajes, suscriptores_telegram.

Si la base está vacía, en Render > Database > SQL, correr:

```sql
CREATE TABLE IF NOT EXISTS usuarios (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(255),
  email VARCHAR(255) UNIQUE NOT NULL,
  rol VARCHAR(50) DEFAULT 'operador',
  activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS robots (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(255),
  descripcion TEXT
);

CREATE TABLE IF NOT EXISTS robot_usuarios (
  robot_id INTEGER NOT NULL,
  usuario_id INTEGER NOT NULL,
  PRIMARY KEY (robot_id, usuario_id)
);

CREATE TABLE IF NOT EXISTS invitaciones (
  id SERIAL PRIMARY KEY,
  codigo VARCHAR(50) UNIQUE NOT NULL,
  robot_id INTEGER NOT NULL,
  creado_por INTEGER NOT NULL,
  vence_en TIMESTAMP,
  usos_max INTEGER DEFAULT 5,
  usos_actuales INTEGER DEFAULT 0,
  activo BOOLEAN DEFAULT TRUE,
  fecha_creacion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alertas (
  id SERIAL PRIMARY KEY,
  robot_id INTEGER NOT NULL,
  tipo VARCHAR(100),
  descripcion TEXT,
  foto_url TEXT,
  fecha_hora TIMESTAMP DEFAULT NOW(),
  atendida BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS notificaciones (
  id SERIAL PRIMARY KEY,
  alerta_id INTEGER NOT NULL,
  mensaje TEXT,
  fecha_envio TIMESTAMP DEFAULT NOW(),
  leida BOOLEAN DEFAULT FALSE,
  estado_envio VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS mensajes (
  id SERIAL PRIMARY KEY,
  robot_id INTEGER NOT NULL,
  usuario_id INTEGER NOT NULL,
  texto TEXT NOT NULL,
  fecha TIMESTAMP DEFAULT NOW(),
  activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS suscriptores_telegram (
  chat_id BIGINT PRIMARY KEY,
  nombre VARCHAR(255),
  activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS telegram_robot_usuarios (
  chat_id BIGINT NOT NULL,
  robot_id INTEGER NOT NULL,
  PRIMARY KEY (chat_id, robot_id)
);
```

## 6. Configurar Google OAuth

1. Entrá a Google Cloud Console
2. Creá un proyecto o usá uno existente
3. Andá a APIs y servicios > Credenciales > Crear credenciales > ID de cliente de OAuth
4. Tipo: Aplicación web
5. Agregá:

Authorized JavaScript origins:

```text
https://tu-app.onrender.com
http://127.0.0.1:5000
```

Authorized redirect URIs:

```text
https://tu-app.onrender.com/callback
http://127.0.0.1:5000/callback
```

6. Copiá el Client ID y Client Secret al `.env`.

## 7. Configurar Webhook de Telegram

Hablá con @BotFather en Telegram, creá el bot y copiá el token.

Una vez que la app está en Render, configurá el webhook:

```bash
curl "https://api.telegram.org/botTU_TOKEN/setWebhook?url=https://tu-app.onrender.com/webhook"
```

Si querés ver si quedó bien:

```bash
curl "https://api.telegram.org/botTU_TOKEN/getWebhookInfo"
```

## 8. Correr en local

```bash
python app.py
```

Entrar a:

```text
http://127.0.0.1:5000
```

Probá:

- Entrar con Google
- Ir a `/panel`
- Ir a `/mis-robots`
- Ir a `/chat?robot=1`

## 9. Desplegar en Render

1. Entrá a Render > New > Web Service
2. Conectá tu repo de GitLab
3. Configurá:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT`
   - Variables de entorno: las mismas del `.env`, pero con `SESSION_COOKIE_SECURE=true`
4. Deploy y esperá que diga **Live**.
5. Entrá a `https://tu-app.onrender.com` y probá el login con Google.

## 10. Problemas comunes

**No me deja entrar con Google:**
Revisá que el redirect URI en Google Cloud sea exactamente `https://tu-app.onrender.com/callback`.

**Telegram no responde:**
Revisá que el webhook esté puesto y que el token en Render sea el mismo de BotFather.

**Error de base de datos:**
Revisá que la `DATABASE_URL` en Render empiece con `postgresql://`.

**El chat no se actualiza:**
Es normal, se actualiza cada 2 segundos con JavaScript. Recargá la página.
