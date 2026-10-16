Arquitectura del Sistema Web de Protud

Introducción

Protud es un proyecto de robótica orientado a la vigilancia y supervisión de establecimientos, como instituciones educativas.

El sistema está diseñado para integrar un robot móvil, una aplicación web y una base de datos, permitiendo a los usuarios supervisar el robot, consultar alertas y administrar la información generada durante su funcionamiento.

Esta documentación describe la arquitectura propuesta para el desarrollo del sistema.

Objetivos del sistema web

La aplicación web de Protud tendrá como objetivos:

- Permitir el acceso de usuarios mediante inicio de sesión.
- Mostrar un panel principal de supervisión.
- Controlar remotamente los movimientos del robot.
- Recibir y visualizar alertas y notificaciones.
- Consultar fotografías capturadas por el robot.
- Registrar y consultar el historial de actividad.
- Permitir la visualización de una cámara en vivo, dependiendo de la disponibilidad del hardware.

Arquitectura general

El sistema se organizará en cuatro componentes principales.

Robot Protud

El robot será el componente físico del proyecto. Contará con motores, controladores electrónicos y sensores.

Se contempla la utilización de ESP32, Arduino Uno y, si está disponible, ESP32-CAM para las funciones de captura de imágenes y transmisión de video.

El robot enviará información al servidor y recibirá instrucciones de movimiento.

Aplicación web

La aplicación web será la interfaz utilizada por los usuarios para interactuar con Protud.

Tendrá un diseño adaptable (responsive), compatible con computadoras y dispositivos móviles.

Sus principales secciones serán:

- Inicio de sesión.
- Panel principal.
- Control remoto.
- Alertas y notificaciones.
- Fotografías.
- Historial de actividad.
- Cámara en vivo.

Servidor y API

El servidor actuará como intermediario entre la aplicación web, la base de datos y el robot.

Sus responsabilidades incluirán:

- Procesar las solicitudes de los usuarios.
- Gestionar la autenticación y los permisos.
- Recibir los eventos enviados por el robot.
- Registrar alertas y actividades.
- Consultar y actualizar la base de datos.
- Transmitir las órdenes autorizadas al robot.

La tecnología específica del servidor se definirá durante la implementación.

Base de datos

Se propone utilizar PostgreSQL como sistema gestor de base de datos relacional.

La base de datos almacenará información relacionada con:

- Usuarios.
- Robots.
- Alertas.
- Registros de actividad.

El diseño de sus entidades y relaciones se encuentra documentado en el archivo "docs/database-schemas.md".

Las fotografías podrán almacenarse como archivos, conservando sus referencias en la base de datos si el diseño definitivo lo requiere.

Comunicación entre componentes

La comunicación general seguirá este proceso:

1. El usuario accede a la aplicación web desde una computadora o celular.
2. La aplicación envía las solicitudes al servidor.
3. El servidor verifica las solicitudes y los permisos correspondientes.
4. Cuando sea necesario, el servidor envía instrucciones al robot.
5. El robot ejecuta las instrucciones y comunica su estado.
6. Los eventos relevantes se registran en PostgreSQL.
7. La aplicación web consulta y presenta la información al usuario.

Se utilizarán mecanismos de comunicación adecuados para cada componente, cuya implementación se definirá y probará durante el desarrollo.

Sistema de alertas

Protud tendrá un sistema de alertas destinado a informar eventos relevantes detectados durante la vigilancia.

El funcionamiento propuesto será:

1. Un sensor detecta un evento.
2. El robot envía la información al servidor.
3. El servidor procesa el evento.
4. La alerta se registra en la base de datos.
5. La aplicación web muestra la notificación al usuario.

Las condiciones de activación de las alertas dependerán de los sensores disponibles y de su configuración.

Cámara y fotografías

Se contempla utilizar un ESP32-CAM para incorporar funciones de captura de fotografías y transmisión de imágenes mediante Wi-Fi.

La cámara en vivo se considera una funcionalidad planificada y estará sujeta a la disponibilidad del módulo, la conexión de red y las pruebas de rendimiento.

Seguridad

La arquitectura deberá contemplar:

- Autenticación de usuarios.
- Control de acceso a las funciones del robot.
- Protección de las credenciales.
- Validación de solicitudes recibidas por el servidor.
- Restricción del acceso directo a PostgreSQL.
- Protección de las comunicaciones cuando corresponda.

Estas medidas deberán implementarse y verificarse durante el desarrollo.

Estado del desarrollo

Este documento describe la arquitectura planificada de Protud y no implica que todas las funciones mencionadas estén implementadas.

La construcción del sistema, las pruebas de comunicación, la configuración de PostgreSQL y la integración del hardware se realizarán progresivamente.

El diseño podrá actualizarse de acuerdo con los resultados de las pruebas y los requisitos del proyecto.



