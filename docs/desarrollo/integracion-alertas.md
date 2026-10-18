# Integración del Sistema de Alertas — PROTUD

**Proyecto:** PROTUD — Sistema de Vigilancia Robótica  
**Fecha de implementación:** 17 de octubre de 2026  
**Área:** Desarrollo de software — Backend y notificaciones  
**Estado:** Integración funcional verificada mediante simulaciones

---

## Introducción

Durante el desarrollo de PROTUD se implementó un sistema de alertas de seguridad mediante la integración de Python, Flask, PostgreSQL y Telegram Bot API.

Esta funcionalidad permite registrar eventos de seguridad, almacenar su información en una base de datos y enviar notificaciones al usuario mediante Telegram.

La implementación constituye una etapa fundamental del backend de PROTUD y prepara la infraestructura necesaria para integrar posteriormente los sensores y la cámara del robot Mini Protud.

Actualmente, el sistema funciona mediante eventos simulados generados desde Flask. La detección física de movimiento todavía no se encuentra integrada.

## Objetivos

El desarrollo de esta funcionalidad tiene como objetivos:

- Registrar eventos de seguridad asociados a un robot.
- Almacenar alertas en una base de datos PostgreSQL.
- Enviar notificaciones mediante Telegram Bot API.
- Registrar el resultado de los intentos de envío.
- Mantener un historial de alertas y notificaciones.
- Establecer una base de software para la futura integración del hardware.

## Tecnologías utilizadas

| Tecnología | Función |
|---|---|
| Python | Lenguaje de programación del backend |
| Flask | Servidor web y gestión de rutas HTTP |
| PostgreSQL | Sistema de gestión de base de datos |
| Psycopg | Adaptador de PostgreSQL para Python |
| Requests | Comunicación HTTP con Telegram |
| Python-dotenv | Carga de variables de entorno |
| Telegram Bot API | Envío de notificaciones |
| Pytest | Ejecución de pruebas automatizadas |
| Visual Studio Code | Entorno de desarrollo |
| Git y GitHub | Control de versiones y documentación |

## Arquitectura del sistema

La arquitectura implementada utiliza Flask como componente central de comunicación entre PostgreSQL y Telegram.

El procedimiento comienza cuando el servidor recibe una solicitud de simulación. Posteriormente, se registra una alerta en la base de datos, se solicita el envío de un mensaje y se almacena el resultado de la operación.

### Flujo de funcionamiento

```text
Solicitud HTTP de simulación
             |
             v
       Servidor Flask
             |
             v
    Registro de alerta
        PostgreSQL
             |
             v
     Servicio Telegram
             |
             v
      Telegram Bot API
             |
             v
   Notificación al usuario
             |
             v
 Registro del estado de envío
        PostgreSQL
```

Esta arquitectura permite separar el almacenamiento de información de los mecanismos de comunicación y notificación.

## Diseño de la base de datos

La base de datos utilizada se denomina `protud`.

El sistema contempla las siguientes tablas:

- `usuarios`
- `robots`
- `alertas`
- `imagenes`
- `notificaciones`

### Registro del robot

Durante las pruebas se verificó la existencia del siguiente registro:

| Campo | Valor |
|---|---|
| Identificador | 1 |
| Nombre | Mini Protud |
| Ubicación | Escuela |
| Estado | inactivo |

El robot permanece registrado como inactivo porque la integración física todavía se encuentra en desarrollo.

### Registro de alertas

La tabla `alertas` almacena eventos de seguridad asociados a los robots registrados.

Entre los datos utilizados se encuentran el identificador de la alerta, el robot relacionado, el tipo de evento, la descripción, la fecha y hora, y el estado de atención.

Durante las pruebas se generaron alertas simuladas de movimiento.

### Registro de notificaciones

La tabla `notificaciones` permite mantener un historial de los mensajes generados por el sistema.

Su estructura incluye:

| Campo | Descripción |
|---|---|
| `id` | Identificador de la notificación |
| `alerta_id` | Identificador de la alerta relacionada |
| `mensaje` | Contenido del mensaje |
| `fecha_envio` | Fecha registrada de la notificación |
| `leida` | Estado de lectura |
| `estado_envio` | Resultado del intento de envío |

Se incorporó la columna `estado_envio` mediante la siguiente instrucción SQL:

```sql
ALTER TABLE notificaciones
ADD COLUMN estado_envio VARCHAR(20) NOT NULL DEFAULT 'pendiente'
CHECK (estado_envio IN ('pendiente', 'enviada', 'fallida'));
```

Los estados permitidos son:

- **Pendiente:** todavía no se confirmó el envío.
- **Enviada:** Telegram confirmó la solicitud de envío.
- **Fallida:** no se completó correctamente el envío.

La confirmación de envío no implica necesariamente que el destinatario haya leído el mensaje.

## Implementación del backend

El backend se desarrolló utilizando Python y Flask.

Su función principal es gestionar las solicitudes HTTP, interactuar con PostgreSQL y coordinar las notificaciones.

### Conexión con PostgreSQL

El archivo `web/app.py` contiene la función `conectar_db()`, encargada de establecer la conexión con PostgreSQL mediante Psycopg.

Los parámetros de conexión se obtienen mediante variables de entorno.

Esta configuración evita incorporar directamente las credenciales dentro del código fuente.

### Servicio de notificaciones de Telegram

Se creó el módulo:

`web/telegram_service.py`

Este archivo contiene la función:

```python
enviar_alerta_telegram(robot, evento, ubicacion)
```

La función recibe información sobre el robot, el evento detectado y la ubicación.

Posteriormente construye el mensaje y realiza una solicitud HTTP a Telegram Bot API.

El resultado permite identificar si Telegram confirmó correctamente la solicitud.

### Registro del estado de las notificaciones

Se desarrolló la función `registrar_notificacion()`, encargada de almacenar el mensaje y su estado de envío.

```python
def registrar_notificacion(alerta_id, mensaje, enviado):
    estado = "enviada" if enviado else "fallida"

    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO notificaciones
                    (alerta_id, mensaje, estado_envio)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (alerta_id, mensaje, estado)
            )
            return cursor.fetchone()[0]
```

La función relaciona cada notificación con una alerta registrada previamente.

### Simulación de eventos de seguridad

Se implementó la ruta HTTP:

`POST /simular-alerta`

Esta ruta permite ejecutar una prueba integrada del sistema.

Al recibir una solicitud:

- Se genera una alerta simulada.
- Se registra el evento en PostgreSQL.
- Se obtiene el identificador de la alerta.
- Se solicita el envío de la notificación mediante Telegram.
- Se almacena el resultado del envío.
- Se devuelve una respuesta con el estado de la operación.

La ruta se utiliza exclusivamente para pruebas de desarrollo local.

## Pruebas y verificaciones

Se realizaron comprobaciones para verificar el funcionamiento del backend y su integración con los servicios utilizados.

### Comprobación de sintaxis

Se ejecutó el siguiente comando:

```powershell
python -m py_compile web/app.py
```

**Resultado:** el archivo superó la comprobación de sintaxis sin errores.

### Pruebas automatizadas

Se utilizó Pytest mediante:

```powershell
python -m pytest web/tests/test_app.py -q
```

Resultado obtenido:

```text
1 passed in 0.60s
```

La prueba automatizada existente se ejecutó satisfactoriamente. Este resultado no representa una cobertura completa de todas las funcionalidades del sistema.

### Ejecución del servidor Flask

El servidor de desarrollo se inició mediante:

```powershell
python web/app.py
```

Dirección local:

`http://127.0.0.1:5000`

### Simulación de una alerta

Se realizó una solicitud HTTP utilizando PowerShell:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/simular-alerta" -Method POST
```

Resultado obtenido:

```text
alerta_id        : 3
registrada       : True
telegram_enviado : True
```

La respuesta confirmó que la alerta número 3 fue registrada y que Telegram aceptó la solicitud de envío.

También se observó la recepción del aviso mediante la aplicación de Telegram en Windows.

### Verificación del historial de notificaciones

Se ejecutó la siguiente consulta en PostgreSQL:

```sql
SELECT id, alerta_id, mensaje, estado_envio
FROM notificaciones
ORDER BY id DESC
LIMIT 5;
```

Resultado:

| ID de notificación | ID de alerta | Estado |
|---|---|---|
| 2 | 3 | enviada |
| 1 | 1 | pendiente |

La notificación número 2 quedó correctamente relacionada con la alerta número 3.

La notificación anterior mantiene el estado pendiente porque fue registrada antes de implementar el seguimiento del estado de envío.

## Problemas encontrados y soluciones

### Error HTTP 400 de Telegram

Durante las primeras pruebas se recibió el mensaje:

`Bad Request: chat not found`

El problema se produjo por utilizar un identificador de conversación incorrecto.

Se verificó el Chat ID y se actualizó la configuración correspondiente.

Posteriormente se consiguió enviar mensajes correctamente.

### Error HTTP 404 en Flask

Durante las pruebas de integración, una ruta de Telegram no fue reconocida inicialmente por el servidor.

Se revisó la ubicación de la función, se guardaron los cambios y se reinició Flask.

La ruta comenzó a responder correctamente.

### Problemas de indentación en Python

Durante el desarrollo se presentaron errores de indentación y ubicación de bloques de código.

Se corrigió la estructura de las funciones y se realizaron comprobaciones utilizando `py_compile`.

Esto permitió continuar con las pruebas sin errores de sintaxis.

## Seguridad y configuración

La configuración privada se gestiona mediante variables de entorno.

El archivo `web/.env` contiene información sensible, como las credenciales de PostgreSQL y el token de Telegram.

Este archivo no debe incorporarse al repositorio público.

También deben excluirse:

- Entornos virtuales de Python.
- Archivos de caché.
- Archivos temporales.
- Credenciales y claves privadas.

Las rutas de simulación y el modo de depuración de Flask se utilizan únicamente durante el desarrollo.

Antes de desplegar el sistema será necesario implementar mecanismos de autenticación, autorización y protección de las rutas HTTP.

## Estado actual del desarrollo

### Funcionalidades implementadas y verificadas

- Conexión entre Flask y PostgreSQL.
- Registro de Mini Protud en la base de datos.
- Registro de alertas simuladas.
- Envío de mensajes mediante Telegram Bot API.
- Integración del servicio de Telegram con Flask.
- Registro de notificaciones en PostgreSQL.
- Almacenamiento del estado de envío.
- Consulta del historial mediante SQL.
- Prueba integrada de alerta y notificación.
- Comprobación de sintaxis y ejecución de una prueba automatizada.

### Funcionalidades pendientes

- Integración de sensores físicos de movimiento.
- Comunicación entre el hardware y el backend.
- Incorporación de ESP32-CAM.
- Captura y almacenamiento de fotografías.
- Asociación de imágenes con eventos de seguridad.
- Mejoras del panel web.
- Gestión de usuarios y permisos.
- Prevención de notificaciones duplicadas.
- Manejo de fallos y reintentos de comunicación.
- Ampliación de las pruebas automatizadas.
- Preparación para un despliegue seguro.

## Próximas etapas

El desarrollo continuará con la mejora del panel web de PROTUD para facilitar la visualización de alertas y notificaciones.

Posteriormente se trabajará en la integración del hardware del robot Mini Protud, permitiendo que los eventos de seguridad se generen a partir de sensores reales.

También se prevé incorporar fotografías obtenidas mediante ESP32-CAM y asociarlas con los eventos registrados.

## Conclusión

La integración de Flask, PostgreSQL y Telegram representa un avance importante en el desarrollo del sistema de vigilancia robótica PROTUD.

Las pruebas realizadas demostraron que el backend puede generar una alerta simulada, almacenarla en PostgreSQL, enviar una notificación mediante Telegram y registrar el resultado de la operación.

Esta implementación proporciona una base funcional para continuar con el desarrollo de las capacidades de vigilancia y comunicación del robot.

**Estado de la etapa:** integración de alertas simuladas implementada y verificada exitosamente.
El próximo objetivo es fortalecer el sistema y conectarlo con eventos originados por el robot físico.
