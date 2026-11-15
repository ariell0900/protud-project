# PROTUD - Robot de Vigilancia

Proyecto Final - Profesor Leonardo Baldelli
Integrantes: Ariel Alfonso - marcelo rodriguez - Emiliano veron -lautaro berger .
Escuela: Proyecto Final 2026

Web para controlar un robot de vigilancia con login de Google, alertas, chat y Telegram.

## Qué hace PROTUD

- Login con Google, sin usuario y contraseña propios, con OAuth2 / OpenID Connect
- Panel con alertas pendientes, alertas de las últimas 24 horas y últimas 5 alertas
- Mis Robots con códigos de invitación tipo `PROTUD-K7Q2`
- Unirse a un robot con código, desde la web o desde Telegram
- Chat en vivo por robot, se actualiza solo cada 2 segundos con polling
- Alertas con foto que llegan a Telegram automáticamente
- Bot de Telegram con `/start`, `/unirme`, `/mis_espacios`, `/ayuda`
- Gestión de usuarios, roles administrador / operador, baja lógica y reactivar
- Probar alertas con `/simular-alerta` y `/probar-telegram` para la demo sin robot físico

## Tecnologías

- Python 3.11 + Flask
- PostgreSQL en Render
- Google OAuth2 / OpenID Connect con google-auth
- Telegram Bot API con requests + Webhook
- Gunicorn para producción
- HTML + CSS + JavaScript puro con Jinja2
- MkDocs Material para el manual
- GitLab con ramas main / develop / feature

## Cómo instalar rápido

Ver manual completo en `docs/manual/instalacion.md`

```bash
git clone https://gitlab.com/TU-USUARIO/protud.git
cd protud
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Entrar a `http://127.0.0.1:5000`

## Documentación

- Manual: `docs/manual/index.md`
- Instalación: `docs/manual/instalacion.md`
- Uso: `docs/manual/uso.md`
- Base de datos: `docs/database-schemas.md`
- Autenticación: `docs/autenticacion.md`
- Arquitectura: `docs/architecture.md`
- Pruebas: `docs/testing.md`

## Ramas GitLab

- `main`: producción, la que está en Render
- `develop`: desarrollo
- `feature/database`: base de datos
- `feature/autenticacion`: login Google
- `feature/chat`: chat por robot
- `feature/alertas`: alertas y panel
- `feature/telegram`: bot y notificaciones
- `feature/docs`: manual y documentación

## Link producción

https://tu-app.onrender.com
