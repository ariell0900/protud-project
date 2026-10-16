```sql
-- =====================================
-- BASE DE DATOS PROTUD
-- Creación de las 3 tablas (16/10/2026)
-- Motor: PostgreSQL
-- Pendiente para el 7/11: tabla registros_actividad
-- =====================================

-- TABLA 1: USUARIOS
-- Personas autorizadas a usar la página web

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL
        CHECK (rol IN ('administrador', 'operador')),
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- TABLA 2: ROBOTS
-- Robots PROTUD registrados en el sistema

CREATE TABLE robots (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    ubicacion VARCHAR(150),
    estado VARCHAR(30)
        CHECK (estado IN ('activo', 'inactivo', 'desconectado')),
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- TABLA 3: ALERTAS
-- Eventos de seguridad que detectan los robots
-- foto_url guarda la ruta de la foto, no la imagen

CREATE TABLE alertas (
    id SERIAL PRIMARY KEY,
    robot_id INTEGER REFERENCES robots(id),
    tipo VARCHAR(50),
    descripcion TEXT,
    foto_url VARCHAR(255),
    fecha_hora TIMESTAMP DEFAULT NOW(),
    atendida BOOLEAN DEFAULT FALSE
);
```

Crea las tres tablas: usuarios, robots y alertas. Avisame cuando hagas el commit y te paso el de datos_prueba.sql.
