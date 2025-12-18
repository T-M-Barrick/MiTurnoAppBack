from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from core.variables import DB_URL

engine = create_engine(DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener sesión en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # finally db.close() significa “cerrá la conexión con la base de datos sí o sí, tanto si todo salió bien como si falló algo”

'''
USE miturno;

WITH RECURSIVE minutos AS (
  SELECT 0 AS m
  UNION ALL
  SELECT m + 5 FROM minutos WHERE m + 5 < 1440
)
INSERT INTO disponibilidad (dia, hora)
SELECT d.dia, DATE_FORMAT(SEC_TO_TIME(m.m * 60), '%H:%i')
FROM (
    SELECT 'lunes' AS dia, 1 AS orden
    UNION SELECT 'martes', 2
    UNION SELECT 'miércoles', 3
    UNION SELECT 'jueves', 4
    UNION SELECT 'viernes', 5
    UNION SELECT 'sábado', 6
    UNION SELECT 'domingo', 7
) AS d
CROSS JOIN minutos m
ORDER BY d.orden, m.m;

INSERT INTO estado_turno (estado) VALUES
('confirmado'),
('cancelado por usuario'),
('cancelado por empresa'),
('cumplido'),
('no cumplido');

WITH RECURSIVE series AS (
    SELECT 30 AS n
    UNION ALL
    SELECT n + 30
    FROM series
    WHERE n + 30 <= 1410
)
INSERT INTO recordatorio (minutos_antes)
SELECT n FROM series;
'''