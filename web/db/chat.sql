-- Tabla del Sistema de Chat de Protud
-- Cada mensaje pertenece a un robot (su equipo) y lo escribe un usuario
CREATE TABLE IF NOT EXISTS mensajes (
    id SERIAL PRIMARY KEY,
    robot_id INTEGER REFERENCES robots(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    texto TEXT NOT NULL,
    fecha TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE
);

