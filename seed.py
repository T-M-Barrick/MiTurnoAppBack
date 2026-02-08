from sqlalchemy.orm import Session

from core import models
from core.database import SessionLocal

def seed_estados_turno(db: Session):
    estados = [
        "CONFIRMADO",
        "CANCELADO_POR_USUARIO",
        "CANCELADO_POR_EMPRESA",
        "CUMPLIDO",
        "NO_CUMPLIDO",
    ]

    existentes = {
        e.estado for e in db.query(models.Estado_Turno).all()
    }

    for estado in estados:
        if estado not in existentes:
            db.add(models.Estado_Turno(estado=estado))

def run_seeds(db: Session):
    seed_estados_turno(db)
    db.commit()

db = SessionLocal()
run_seeds(db)
db.close()

print("✅ Seeds ejecutados correctamente")