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
