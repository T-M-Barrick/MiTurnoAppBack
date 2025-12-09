from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from core.database import SessionLocal
from core import models, crud, mensajes, auxiliares

def formatear_fecha_hora_turno(fecha_turno: datetime, ahora: datetime):
    dh = auxiliares.extraer_dia_y_hora(fecha_turno)
    nombre_dia = dh[0]
    hora = dh[1]
    fecha_str = fecha_turno.strftime("%d/%m")
    hora_str = hora.strftime("%H:%M")
    
    # MISMO DÍA
    if fecha_turno.date() == ahora.date():
        return f"hoy {nombre_dia} {fecha_str} a las {hora_str} hs"
    
    # MAÑANA
    if fecha_turno.date() == ahora.date() + timedelta(days=1):
        return f"mañana {nombre_dia} {fecha_str} a las {hora_str} hs"
    
    # OTRO DÍA
    return f"{nombre_dia} {fecha_str} a las {hora_str} hs"

def enviar_recordatorios():
    db = SessionLocal()

    ahora = datetime.utcnow()

    # Buscar turnos cuyo recordatorio debe enviarse AHORA
    turnos = (
        db.query(models.Turno)
        .options(
            joinedload(models.Turno.usuario).selectinload(models.Usuario.telefonos),
            joinedload(models.Turno.empresa)
        )
        .join(models.Recordatorio)
        .filter(
            models.Turno.fecha_hora - func.make_interval(
                0,0,0,0,0, models.Recordatorio.minutos_antes
            ) <= ahora,
            models.Turno.fecha_hora > ahora,
        )
        .all()
    )

    for turno in turnos:

        telefono = turno.usuario.telefonos[0].numero  # o el que corresponda
        cuando = formatear_fecha_hora_turno(turno.fecha_hora, ahora):

        # ENVIAR SMS
        mensajes.enviar_sms(telefono, f'Recordatorio: tenés un turno en {turno.empresa.nombre} para {cuando}')

    db.close()

def limpiar_tokens_expirados():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        db.query(models.Blacklist).filter(models.Blacklist.expires_at < now).delete()
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    'scheduler.add_job(enviar_recordatorios, "cron", minute="0,5,10,15,20,25,30,35,40,45,50,55")'
    scheduler.add_job(limpiar_tokens_expirados, "interval", hours=24)
    scheduler.start()

'''
from core.crud import eliminar_turno

# Limpieza periódica de los turnos vencidos de la tabla Turno. Si están vencidos hace una semana o más, se pasan a la tabla Historial

def limpiar_turnos_vencidos():
    db = SessionLocal()
    try:
        hace_7_dias = datetime.now() - timedelta(days=7)
        turnos_vencidos = db.query(models.Turno).filter(models.Turno.fecha_hora < hace_7_dias).all()
        for turno in turnos_vencidos:
            eliminar_turno(db, turno)
    except Exception as e:
        print(f"Error al limpiar turnos: {e}")  # o usar logging
    finally:
        db.close()
'''