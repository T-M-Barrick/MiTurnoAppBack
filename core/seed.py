from datetime import time

from core.database import SessionLocal
from core.models import Estado_Turno, Disponibilidad, Recordatorio

db = SessionLocal()

try:
    # -----------------------------
    # 1️⃣ Insertar estados de turno
    # -----------------------------
    estados = [
        "confirmado",
        "cancelado por usuario",
        "cancelado por empresa",
        "cumplido",
        "no cumplido"
    ]
    for e in estados:
        if not db.query(Estado_Turno).filter_by(estado=e).first():
            db.add(Estado_Turno(estado=e))
    db.commit()
    print("Estados insertados ✅")

    # -----------------------------
    # 2️⃣ Insertar recordatorios de 30 a 1410 de 30 en 30
    # -----------------------------
    for minutos in range(30, 1411, 30):
        if not db.query(Recordatorio).filter_by(minutos_antes=minutos).first():
            db.add(Recordatorio(minutos_antes=minutos))
    db.commit()
    print("Recordatorios insertados ✅")

    # -----------------------------
    # 3️⃣ Insertar disponibilidades (opcional simple)
    # -----------------------------
    dias = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]
    for dia in dias:
        hora = time(9,0)
        while hora <= time(17,0):
            if not db.query(Disponibilidad).filter_by(dia=dia, hora=hora).first():
                db.add(Disponibilidad(dia=dia, hora=hora))
            # Avanzar 5 minutos
            h = (hora.hour*60 + hora.minute + 5) // 60
            m = (hora.hour*60 + hora.minute + 5) % 60
            hora = time(h,m)
    db.commit()
    print("Disponibilidades insertadas ✅")

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