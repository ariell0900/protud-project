# PROTUD - Pruebas

No tenemos tests automáticos. Las pruebas son manuales, con checklist.

## 1. Login

- [ ] Entrar con Google como usuario nuevo -> queda como operador
- [ ] Entrar con Google como usuario existente -> entra directo
- [ ] Entrar como usuario dado de baja -> no deja entrar, muestra inactivo
- [ ] Salir -> cierra sesión, no deja entrar a /panel sin login
- [ ] Entrar a /panel sin login -> redirige a login
- [ ] Entrar a /usuarios como operador -> te saca

## 2. Mis Robots y códigos

- [ ] Admin crea código -> se genera PROTUD-XXXX
- [ ] Código dura 24hs, 5 usos
- [ ] Operador se une con código válido en web -> aparece robot
- [ ] Operador se une con código vencido -> error
- [ ] Operador se une con código ya usado 5 veces -> error
- [ ] Operador se une con código revocado -> error
- [ ] Admin revoca código -> ya no sirve

## 3. Telegram

- [ ] Mandar /start -> responde bienvenida
- [ ] Mandar /unirme PROTUD-XXXX válido -> se une
- [ ] Mandar /unirme con código inválido -> error
- [ ] Mandar /mis_espacios -> muestra robots
- [ ] Mandar /ayuda -> muestra comandos
- [ ] Generar alerta con /simular-alerta -> llega a Telegram con foto
- [ ] Probar /probar-telegram -> llega mensaje de prueba

## 4. Chat

- [ ] Entrar a /chat?robot=1 con acceso -> muestra chat
- [ ] Entrar a /chat?robot=1 sin acceso -> te saca
- [ ] Mandar mensaje -> aparece en menos de 2 segundos
- [ ] Otro usuario ve el mensaje sin recargar
- [ ] Operador borra su mensaje -> se borra
- [ ] Operador intenta borrar mensaje de otro -> no puede
- [ ] Admin borra cualquier mensaje -> se borra

## 5. Alertas

- [ ] Ir a /alertas -> muestra pendientes y atendidas
- [ ] Apretar Atender -> pasa a atendidas
- [ ] Apretar Deshacer -> vuelve a pendientes
- [ ] Ir a /panel -> muestra pendientes, últimas 24hs y últimas 5
- [ ] Simular alerta -> aparece en /alertas y en /panel

## 6. Usuarios

- [ ] Admin entra a /usuarios -> ve lista
- [ ] Cambiar rol operador a administrador -> cambia
- [ ] Cambiar rol administrador a operador -> cambia
- [ ] Dar de baja usuario -> queda activo=false, no puede entrar
- [ ] Reactivar usuario -> queda activo=true, puede entrar de nuevo

## 7. Deploy

- [ ] App en Render está Live
- [ ] Login con Google en producción anda
- [ ] Webhook de Telegram configurado
- [ ] Base de datos conectada
