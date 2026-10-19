# Registro de avances — PROTUD

## Etapa 1 (objetivo)
El robot saca una foto con la ESP32-CAM al detectar un evento, manda una alerta por WiFi con la foto y el usuario la ve en la web y en Telegram.

---

## 16/10/2026 — Base de datos
- Se instaló PostgreSQL y se creó la base `protud`.
- Tablas iniciales: `usuarios`, `robots`, `alertas` (probadas con datos simulados).
- Se armó el Mini Protud de cartón con las medidas de los diseños para la presentación.

## 17/10/2026 — Avisos por Telegram
- Decisión: **Telegram** es el canal principal de avisos; el historial queda en la web.
- Se creó el bot **@ProtudVigilanciaBot** y se recibió la primera alerta desde Python.
- Integración PostgreSQL + Flask + Telegram: la alerta se guarda, se envía y se registra si el envío salió bien.
- Nuevas tablas: `imagenes` y `notificaciones` (total: 5).

## 18/10/2026 — Página web
- Portada con Bootstrap: logo, título "Siempre atento, siempre en movimiento", tarjetas de vista previa y pie de página con Instagram y GitHub.
- `/alertas`: etiquetas Pendiente/Atendida, fecha formateada, botones **Marcar como atendida** y **Deshacer** (rutas POST que actualizan PostgreSQL).
- `/fotos`: lista de fotos de ejemplo.
- `/panel`: números reales de la base (pendientes, últimas 24 h, imágenes) y tabla con las 5 alertas más nuevas.
- `/robot`: tarjeta "Última alerta" con datos reales e imagen de ejemplo del diseño conceptual.
- Decisiones: cada usuario ve solo sus robots y sus fotos; las fotos no se borran, quedan en historial.

## 19/10/2026 — Presentación (Evaluación de capacidades)
- En `/robot` se agregó el botón **Enviar alerta de prueba**, que llama a `/simular-alerta`: guarda en PostgreSQL, manda a Telegram y el panel se actualiza.

---

## Pendientes
- [ ] Que el interruptor "Avisos de Telegram" funcione de verdad (hoy es solo visual).
- [ ] Inicio de sesión con Google (OAuth2) y tabla de usuarios con baja lógica.
- [ ] Área privada: Alertas, Imágenes, Usuarios y Panel solo después de iniciar sesión.
- [ ] Sección "Mis robots" con "Conectar robot" y aviso estilo logro al conectarse.
- [ ] Programar la ESP32-CAM: moverse, girar y esquivar obstáculos con el sensor.
- [ ] Conectar la ESP32-CAM a la web en la misma red.
- [ ] Imprimir el chasis 3D del Mini Protud.
- [ ] Crear `requirements.txt` y correo propio de Protud.
- [ ] Manual en `docs/manual` con mkdocs (entrega del 7/11).
- [ ] Plan para que funcione sin internet (servidor del colegio).
