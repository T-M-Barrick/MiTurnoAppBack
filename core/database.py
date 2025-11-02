from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from core.variables import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener sesión en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() # finally db.close() significa “cerrá la conexión con la base de datos sí o sí, tanto si todo salió bien como si falló algo”