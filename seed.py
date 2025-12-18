from datetime import time, datetime, timedelta

from core.database import SessionLocal
from core.models import Disponibilidad

db = SessionLocal()

try:
    # 1️⃣ Limpiar la tabla y reiniciar autoincrement
    db.query(Disponibilidad).delete()  # Borra todos los registros
    db.execute("ALTER TABLE disponibilidad AUTO_INCREMENT = 1")  # Reinicia IDs
    db.commit()

    # 2️⃣ Insertar disponibilidades de 5 en 5 minutos por día
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    intervalo = 5  # minutos

    for dia in dias:
        current_time = time(0, 0)
        while current_time < time(24, 0):
            db.add(Disponibilidad(dia=dia, hora=current_time))

            # Avanzar 5 minutos
            current_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=intervalo)).time()

        # Commit por día para no saturar la memoria
        db.commit()

    print("Tabla Disponibilidad poblada correctamente.")

finally:
    db.close()

'''
from sqlalchemy.orm import Session

from core import models

def seed_estados_turno(db: Session):
    estados = [
        "confirmado",
        "cancelado por usuario",
        "cancelado por empresa",
        "cumplido",
        "no cumplido",
    ]

    existentes = {
        e.estado for e in db.query(models.Estado_Turno).all()
    }

    for estado in estados:
        if estado not in existentes:
            db.add(models.Estado_Turno(estado=estado))


def seed_recordatorios(db: Session):
    existentes = db.query(models.Recordatorio).count()
    if existentes > 0:
        return

    for minutos in range(30, 1411, 30):
        db.add(models.Recordatorio(minutos_antes=minutos))

from datetime import time, timedelta, datetime

def seed_disponibilidades(db):
    if db.query(models.Disponibilidad).count() > 0:
        return

    dias = [
        "lunes", "martes", "miércoles",
        "jueves", "viernes", "sábado", "domingo"
    ]

    for dia in dias:
        current = time(0, 0)
        while current < time(23, 59):
            db.add(models.Disponibilidad(dia=dia, hora=current))
            current = (
                datetime.combine(datetime.today(), current)
                + timedelta(minutes=5)
            ).time()



def run_seeds(db: Session):
    seed_disponibilidades(db)
    seed_estados_turno(db)
    seed_recordatorios(db)
    db.commit()
'''