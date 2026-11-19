PROTUD – Pruebas del sistema

Para comprobar que el sistema PROTUD funciona correctamente, vamos a realizar distintas pruebas de forma manual. En cada apartado se revisará que las funciones principales trabajen como corresponde.

1. Inicio de sesión

- [ ] Probar ingresar con una cuenta de Google nueva.
- [ ] Comprobar que un usuario que ya tiene cuenta pueda entrar.
- [ ] Verificar que un usuario dado de baja no pueda ingresar.
- [ ] Comprobar que al cerrar sesión se salga correctamente.
- [ ] Intentar entrar al panel sin iniciar sesión.
- [ ] Verificar que un operador no pueda entrar a la sección de usuarios.

2. Robots y códigos de acceso

- [ ] Comprobar que el administrador pueda crear un código.
- [ ] Verificar que el código se genere correctamente con el nombre PROTUD.
- [ ] Comprobar que el código dure 24 horas y permita 5 usos.
- [ ] Probar unir un robot usando un código válido.
- [ ] Probar ingresar un código vencido.
- [ ] Comprobar qué pasa cuando el código ya llegó a sus 5 usos.
- [ ] Verificar que un código revocado ya no permita ingresar.

3. Funcionamiento de Telegram

- [ ] Enviar el comando /start y comprobar que llegue el mensaje de bienvenida.
- [ ] Probar el comando /unirme con un código válido.
- [ ] Probar el mismo comando con un código incorrecto.
- [ ] Enviar /mis_espacios para ver los robots vinculados.
- [ ] Enviar /ayuda para consultar los comandos disponibles.
- [ ] Simular una alerta y comprobar que llegue a Telegram con una foto.
- [ ] Probar el envío de un mensaje de prueba.

4. Chat del sistema

- [ ] Comprobar que un usuario autorizado pueda entrar al chat.
- [ ] Verificar que alguien sin permiso no pueda acceder.
- [ ] Enviar un mensaje y comprobar que aparezca rápidamente.
- [ ] Verificar que otro usuario pueda verlo sin actualizar la página.
- [ ] Comprobar que cada operador pueda borrar sus propios mensajes.
- [ ] Verificar que un operador no pueda borrar mensajes de otras personas.
- [ ] Comprobar que el administrador pueda borrar cualquier mensaje.

5. Sistema de alertas

- [ ] Entrar a la sección de alertas y comprobar que aparezcan las pendientes y las atendidas.
- [ ] Probar el botón Atender.
- [ ] Comprobar que el botón Deshacer devuelva la alerta a pendientes.
- [ ] Revisar que el panel muestre las alertas de las últimas 24 horas y las últimas 5.
- [ ] Generar una alerta de prueba y verificar que aparezca en el panel y en la sección de alertas.

6. Administración de usuarios

- [ ] Comprobar que el administrador pueda ver la lista de usuarios.
- [ ] Probar cambiar un usuario de operador a administrador.
- [ ] Probar cambiar un administrador a operador.
- [ ] Dar de baja un usuario y comprobar que ya no pueda ingresar.
- [ ] Reactivar un usuario y verificar que pueda volver a entrar.

7. Publicación del sistema

- [ ] Comprobar que la página esté funcionando en Render.
- [ ] Verificar que el inicio de sesión con Google funcione correctamente.
- [ ] Revisar que Telegram esté conectado.
- [ ] Comprobar que la base de datos esté funcionando.

Conclusión:

Con estas pruebas buscamos comprobar que todas las partes de PROTUD funcionen correctamente, tanto la página web como el sistema de alertas, los robots y Telegram. Si encontramos algún error, lo corregiremos para que el sistema esté listo para su presentación.
