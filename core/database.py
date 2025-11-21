from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from core.variables import DB_URL

engine = create_engine(DB_URL)

# 🔥 TEST DE CONEXIÓN
try:
    with engine.connect() as conn:
        print("✅ CONECTADO A LA BASE DE DATOS")
except Exception as e:
    print("❌ ERROR DE CONEXIÓN A LA BASE DE DATOS:", e)

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

INSERT INTO disponibilidad (dia, hora)
WITH RECURSIVE minutos AS (
  SELECT 0 AS m
  UNION ALL
  SELECT m + 5 FROM minutos WHERE m + 5 < 1440
)
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
'''