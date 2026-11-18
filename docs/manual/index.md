PROTUD – Manual de instalación y uso

Proyecto: PROTUD – Robot de Vigilancia
Materia: Proyecto Final
Profesor: Leonardo Baldelli
Integrantes: Ariel Alfonso – Equipo PROTUD
Tecnologías utilizadas: Python, Flask, PostgreSQL, Google OAuth2, Telegram y Render.

¿De qué trata el proyecto?

PROTUD es un sistema que desarrollamos para poder controlar y monitorear un robot de vigilancia desde una página web.

La idea principal es que los usuarios puedan ver las alertas que genera el robot, recibir notificaciones por Telegram y comunicarse mediante un chat. También permite agregar otros usuarios utilizando códigos de invitación.

Para entrar a la página usamos una cuenta de Google, así no es necesario crear otro usuario y contraseña.

Funciones de PROTUD

La página tiene distintas opciones que permiten utilizar el sistema:

- Iniciar sesión con Google.
- Ver las alertas que genera el robot.
- Consultar los robots que tenemos vinculados.
- Crear códigos para invitar a otros usuarios.
- Unirse a un robot colocando un código.
- Utilizar el chat para comunicarse.
- Ver las alertas y sus fotografías.
- Marcar una alerta como atendida.
- Recibir notificaciones mediante Telegram.
- Administrar los usuarios que tienen acceso al sistema.

Usuarios y permisos

En PROTUD tenemos dos tipos de usuarios: administrador y operador.

Administrador:

Es el que tiene más permisos dentro de la página. Puede crear códigos de invitación, administrar los usuarios, cambiar sus roles, dar de baja o reactivar cuentas y eliminar mensajes del chat.

También puede realizar pruebas para comprobar que las alertas y Telegram funcionen correctamente.

Operador:

Es el usuario que utiliza las funciones principales del sistema. Puede vincularse con robots mediante códigos, consultar las alertas, entrar al chat y enviar mensajes.

La diferencia es que no puede acceder a la parte de administración ni modificar los permisos de otros usuarios.

Archivos y carpetas del proyecto

Para organizar mejor el proyecto, separamos los archivos según la función que cumple cada uno.

El archivo "app.py" es uno de los más importantes porque contiene las rutas y las funciones principales de la aplicación.

También tenemos:

- "telegram_service.py": se utiliza para enviar mensajes y alertas a Telegram.
- "requirements.txt": contiene las librerías que necesita el proyecto.
- "mkdocs.yml": sirve para configurar el manual.

En la carpeta "templates" están los archivos HTML de las distintas páginas, como el inicio de sesión, el panel, Mis Robots, el chat y las alertas.

En "static" guardamos las imágenes y el logo que aparecen en la página.

La carpeta "docs" contiene los archivos donde explicamos cómo funciona el sistema, cómo instalarlo y cómo está organizada la base de datos.

Base de datos

Para guardar los datos de PROTUD utilizamos PostgreSQL, que está conectada al proyecto mediante Render.

Tenemos varias tablas para guardar la información:

- "usuarios": guarda los datos de los usuarios.
- "robots": contiene los robots registrados.
- "robot_usuarios": relaciona los usuarios con los robots.
- "invitaciones": guarda los códigos que se utilizan para unirse.
- "alertas": almacena las alertas generadas.
- "notificaciones": guarda las notificaciones.
- "mensajes": contiene los mensajes del chat.
- "suscriptores_telegram": registra los usuarios que utilizan Telegram.
- "telegram_robot_usuarios": relaciona las cuentas de Telegram con los robots.

El diagrama de la base de datos se encuentra en el archivo "database-schemas.md".

Funcionamiento del código

La mayor parte del funcionamiento está dentro de "app.py". Ahí se encuentran las funciones para iniciar sesión, controlar los permisos, crear invitaciones, unir usuarios a los robots y administrar el chat.

También se encuentra la parte que recibe los mensajes de Telegram y permite realizar algunas pruebas, como generar alertas de ejemplo.

Cómo consultar el manual

El manual está dividido en dos partes para que sea más fácil encontrar la información:

- Instalación: explica los pasos necesarios para instalar y poner en funcionamiento PROTUD.
- Uso: explica cómo ingresar a la página y utilizar sus diferentes opciones.

Con este manual buscamos dejar explicado cómo está organizado el proyecto y cómo puede utilizarse.
