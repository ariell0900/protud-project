# PROTUD - Autenticación OAuth2 / OpenID

## 1. Sistema usado: Google OAuth2 + OpenID Connect

No usamos usuario y contraseña propios. Usamos Google.

### Flujo completo

1. Usuario aprieta "Entrar con Google" en `/`
2. Va a `/login` y redirige a Google
3. Google devuelve a `/callback`
4. En `/callback` verificamos el `id_token` con `google.oauth2.id_token.verify_oauth2_token`
5. Sacamos `email`, `name`, `picture` del token
6. Si el email no existe en `usuarios`, lo creamos como `operador`
7. Si existe pero está con `activo = false`, no lo dejamos entrar
8. Guardamos en sesión: `session['usuario_id']`, `session['email']`, `session['rol']`, `session['nombre']`

### Archivos y código clave

- `app.py` -> `login()`, `callback()`, `logout()`
- `app.py` -> decoradores `login_required` y `admin_required`
- Variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- Redirect URI: `https://tu-app.onrender.com/callback`
- En local: `http://127.0.0.1:5000/callback`

## 2. Roles

### Administrador

- Puede crear códigos de invitación y revocarlos
- Puede ver y gestionar usuarios en `/usuarios`
- Puede cambiar roles
- Puede dar de baja y reactivar usuarios
- Puede borrar cualquier mensaje del chat
- Puede probar alertas con `/simular-alerta` y `/probar-telegram`

### Operador

- Puede unirse a robots con código
- Puede ver sus robots en `/mis-robots`
- Puede chatear y ver alertas de sus robots
- Solo puede borrar sus propios mensajes
- No puede entrar a `/usuarios`

## 3. Modificaciones de usuarios - Solo Admin

Ruta: `/usuarios`

El admin puede:

- Cambiar rol: `operador` <-> `administrador`
  - Ruta: `POST /usuarios/<id>/cambiar-rol`
- Ver lista completa: nombre, email, rol, activo

Un operador NO puede entrar a `/usuarios`, lo saca con `admin_required`.

## 4. Bajas lógicas

NO borramos usuarios de la base. Usamos el campo `activo` en la tabla `usuarios`.

**Dar de baja:** `POST /usuarios/<id>/baja`

```sql
UPDATE usuarios SET activo = false WHERE id = %s
```

El usuario dado de baja no puede entrar aunque tenga Google válido. En `callback` y en `login_required` se verifica `activo`.

**Reactivar:** `POST /usuarios/<id>/reactivar`

```sql
UPDATE usuarios SET activo = true WHERE id = %s
```

**En mensajes:** cuando un usuario se da de baja, sus mensajes quedan, pero no puede escribir más.

## 5. Protección de rutas

Todas las rutas importantes tienen `@login_required`:

- `/panel`, `/mis-robots`, `/chat`, `/alertas`, `/usuarios`

Solo admin:

- `/usuarios`, `/simular-alerta`, `/probar-telegram`, `/crear-codigo`

Protección por robot:

- `usuario_puede_ver_robot()` en `/chat` y `/api/mensajes` para que un usuario no vea el chat de un robot al que no pertenece.

## 6. Cómo probarlo para la demo

1. Entrar con Google como admin
2. Ir a `/usuarios`
3. Cambiar a un compañero a `administrador`
4. Darlo de baja -> intentar entrar con su Google -> no lo deja
5. Reactivarlo -> ya puede entrar de nuevo
6. Probar entrar a `/usuarios` como operador -> te saca
7. Probar entrar a `/chat?robot=2` sin tener acceso -> te saca
