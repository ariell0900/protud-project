# PROTUD - Manual de Instalación y Uso

**Proyecto:** PROTUD - Robot de Vigilancia
**Materia:** Proyecto Final
**Profesor:** Leonardo Baldelli
**Integrantes:** Ariel Alfonso - Equipo Protud
**Tecnologías:** Python + Flask + PostgreSQL + Google OAuth2 / OpenID + Telegram Bot API + Render + MkDocs

---

## ¿Qué es PROTUD?

PROTUD es una aplicación web para controlar y monitorear un robot de vigilancia.

Permite ver alertas en tiempo real, chatear por robot, invitar usuarios con códigos y recibir notificaciones por Telegram.

No usa usuario y contraseña propios. El acceso es con cuenta de Google, usando OAuth2 y OpenID Connect.

## ¿Qué puede hacer?

- Entrar con Google, sin registrarse a mano
- Ver panel con alertas pendientes, alertas de las últimas 24 horas y últimas 5 alertas
- Ver y gestionar Mis Robots
- Crear códigos de invitación tipo `PROTUD-K7Q2`
- Unirse a un robot con código, desde la web o desde Telegram
- Chatear en vivo por robot, se actualiza solo cada 2 segundos
- Ver alertas con foto, marcarlas como atendidas o deshacer
- Recibir alertas por Telegram
- Usar el bot de Telegram con comandos `/start`, `/unirme`, `/mis_espacios`, `/ayuda`
- Gestionar usuarios: cambiar rol administrador / operador, dar de baja y reactivar

## Roles

### Administrador
- Puede crear códigos de invitación
- Puede revocar códigos
- Puede ver y gestionar usuarios en `/usuarios`
- Puede cambiar roles
- Puede dar de baja y reactivar usuarios
- Puede borrar cualquier mensaje del chat
- Puede probar alertas con `/simular-alerta` y `/probar-telegram`

### Operador
- Puede unirse a robots con código
- Puede ver sus robots en `/mis-robots`
- Puede chatear
- Puede ver alertas de sus robots
- Solo puede borrar sus propios mensajes
- No puede entrar a `/usuarios`

## Estructura del proyecto
protud/
├── app.py                  -> App principal: rutas, login Google, Mis Robots, Chat, Alertas, Webhook Telegram
├── telegram_service.py     -> Funciones para enviar alertas a Telegram
├── requirements.txt        -> Dependencias: Flask, gunicorn, psycopg2, google-auth, requests, etc.
├── mkdocs.yml              -> Configuración del manual con MkDocs
├── templates/
│   ├── index.html          -> Página principal / login
│   ├── panel.html          -> Panel de alertas
│   ├── mis_robots.html     -> Mis Robots, crear código, unirse con código
│   ├── chat.html           -> Chat por robot
│   ├── alertas.html        -> Lista de alertas pendientes y atendidas
│   ├── usuarios.html       -> Gestión de usuarios (solo admin)
│   └── base.html           -> Plantilla base con menú
├── static/
│   ├── logo.jpg
│   └── robot.jpg
└── docs/
    ├── database-schemas.md -> Diagrama Entidad-Relación de la base de datos
    ├── autenticacion.md    -> Documentación de OAuth2, usuarios y bajas lógicas
    └── manual/
        ├── index.md        -> Este archivo: presentación
        ├── instalacion.md  -> Cómo instalar y desplegar
        └── uso.md          -> Cómo usar la app paso a paso




## Base de datos

Base de datos: PostgreSQL en Render

Tablas:
- `usuarios` - usuarios que entran con Google
- `robots` - robots de vigilancia
- `robot_usuarios` - unión muchos a muchos entre usuarios y robots
- `invitaciones` - códigos tipo `PROTUD-XXXX`
- `alertas` - alertas generadas por los robots
- `notificaciones` - notificaciones generadas por cada alerta
- `mensajes` - mensajes del chat por robot
- `suscriptores_telegram` - usuarios de Telegram que hablaron con el bot
- `telegram_robot_usuarios` - unión entre chat de Telegram y robot

El diagrama completo está en `docs/database-schemas.md`.

## Código comentado

Todo el código en `app.py` está comentado en español, función por función:

- `login_required` - obliga a estar logueado
- `admin_required` - obliga a ser administrador
- `usuario_puede_ver_robot` - verifica si el usuario tiene acceso a ese robot
- `login()` y `callback()` - flujo de Google OAuth2
- `crear_invitacion()` - genera código `PROTUD-XXXX`
- `unirse_con_codigo()` - une al usuario con el código
- `chat()` y `api_mensajes()` - chat en vivo
- `webhook()` - recibe mensajes de Telegram
- `simular_alerta()` y `probar_telegram()` - pruebas para el admin

## Cómo leer este manual

1. Si querés instalarlo, andá a **Instalación**
2. Si ya está instalado y querés usarlo, andá a **Uso**
