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
