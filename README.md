# PROTUD 🤖

**Siempre atento, siempre en movimiento.**
Protud recorre, detecta y te avisa al instante.

PROTUD es un robot móvil de vigilancia desarrollado por el Equipo Protud (EEST N°4). Recorre un área, detecta eventos, toma fotos y avisa al usuario. Todo se ve y se controla desde una página web.

---

## Estado del proyecto

| Parte | Estado |
|---|---|
| Prototipo 1 (cartón, 2 ruedas, control por Bluetooth) | ✅ Funciona |
| Mini Protud (chasis 3D, ESP32-CAM, 2 motores DC, sensor ultrasónico) | 🔧 En construcción |
| Base de datos PostgreSQL | ✅ Funciona (5 tablas) |
| Página web Flask + Bootstrap | ✅ Funciona en local |
| Alertas por Telegram | ✅ Funciona con alertas simuladas |
| Inicio de sesión con Google (OAuth2) | 🔧 En progreso |
| Conexión robot ↔ web | ⏳ Pendiente |

---

## Cómo funciona

```
Robot (ESP32-CAM)  →  detecta un evento y saca una foto
        ↓
Web Flask          →  guarda la alerta en PostgreSQL
        ↓
Telegram           →  avisa al usuario al instante (@ProtudVigilanciaBot)
        ↓
Panel web          →  historial de alertas y fotos
```

---

## Estructura del repositorio

```
protud-project/
├── firmware/   código del robot (Arduino y ESP32)
├── web/        página web en Flask + conexión a PostgreSQL
│   ├── templates/   páginas HTML
│   └── static/      logo, estilos e imágenes
├── hardware/   diseños y componentes
├── media/      fotos y videos del proyecto
└── docs/       documentación
```

---

## Tecnologías

- **Robot:** ESP32-CAM, motores DC, sensor ultrasónico
- **Web:** Python, Flask, Bootstrap, JavaScript
- **Base de datos:** PostgreSQL
- **Avisos:** Bot de Telegram

---

## Cómo correr la web en tu compu

1. Clonar el repo y entrar a `web/`
2. Crear el entorno virtual e instalar dependencias:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```
3. Crear la base `protud` en PostgreSQL.
4. Crear un archivo `.env` con tus datos (no se sube al repo):
   ```
   DB_PASSWORD=...
   TELEGRAM_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
5. Iniciar: `python app.py` y abrir http://127.0.0.1:5000

---

## Secciones de la web

| Ruta | Qué hace |
|---|---|
| `/` | Portada pública |
| `/login` | Inicio de sesión |
| `/panel` | Resumen: alertas pendientes, últimas 24 h, imágenes y últimas 5 alertas |
| `/alertas` | Lista de alertas; marcar como atendida o deshacer |
| `/fotos` | Fotos tomadas por el robot |
| `/robot` | Página del robot: cámara (imagen de ejemplo), estado, última alerta y botón de alerta de prueba |
| `/simular-alerta` | Crea una alerta de prueba, la guarda y la manda por Telegram |

---

## Equipo

- **Desarrollo web:** Ariel Alfonso
- **Proyecto:** Equipo Protud — EEST N°4

📷 Instagram: [@protud_](https://instagram.com/protud_)
