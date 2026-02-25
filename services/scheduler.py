from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from core.database import SessionLocal
from core import models, mensajes, auxiliares, timezone

def formatear_fecha_hora_turno(fecha_hora_turno_aware_utc: datetime, ahora_aware_utc: datetime) -> str:

    # Garantía defensiva (por si alguien se equivoca)
    fecha_hora_turno_aware_utc = timezone.ensure_utc(fecha_hora_turno_aware_utc)
    ahora_aware_utc = timezone.ensure_utc(ahora_aware_utc)

    # Convertimos una sola vez a local
    fecha_hora_turno_aware_local = timezone.utc_to_local(fecha_hora_turno_aware_utc) # lo convierte a aware horario local cambiándole la hora
    ahora_aware_local = timezone.utc_to_local(ahora_aware_utc) # lo convierte a aware horario local cambiándole la hora

    dia_local = fecha_hora_turno_aware_local.weekday() # devuelve 0, 1, 2, ..., 6
    nombre_dia = auxiliares.mapear_nombre_dia_semana(dia_local) # le ponemos nombre a dia_local

    fecha_local_str = fecha_hora_turno_aware_local.strftime("%d/%m") # pasamos al formato correspondiente en string
    hora_local_str = fecha_hora_turno_aware_local.strftime("%H:%M") # pasamos al formato correspondiente en string

    # MISMO DÍA (en horario local)
    if fecha_hora_turno_aware_local.date() == ahora_aware_local.date():
        return f"hoy {nombre_dia} {fecha_local_str} a las {hora_local_str} hs"

    # MAÑANA (en horario local)
    if fecha_hora_turno_aware_local.date() == ahora_aware_local.date() + timedelta(days=1):
        return f"mañana {nombre_dia} {fecha_local_str} a las {hora_local_str} hs"

    # OTRO DÍA
    return f"{nombre_dia} {fecha_local_str} a las {hora_local_str} hs"

def enviar_recordatorios():
    db = SessionLocal()

    try:
        ahora_aware_utc = timezone.now_utc() # aware UTC
        ahora_naive_utc = timezone.to_naive_utc(ahora_aware_utc) # naive UTC (DB)

        # Buscar turnos cuyo recordatorio debe enviarse AHORA
        turnos = (
            db.query(models.Turno)
            .options(
                joinedload(models.Turno.usuario).selectinload(models.Usuario.telefonos),
                joinedload(models.Turno.sucursal).joinedload(models.Sucursal.empresa),
            )
            .filter(
                models.Turno.recordatorio_fecha_hora != None,
                models.Turno.recordatorio_fecha_hora <= ahora_naive_utc,
                models.Turno.recordatorio_enviado == False,
                models.Turno.estado_turno_usuario_id == 1, # esto evita enviar recordatorios de turnos cancelados
                models.Turno.eliminado_por_usuario == False,
                models.Turno.fecha_hora > ahora_naive_utc,
            )
            # Con with_for_update(skip_locked=True) las filas seleccionadas quedan bloqueadas y
            # si otro worker ya las bloqueó, las salta y así evito enviar el mismo SMS dos veces en paralelo
            .with_for_update(skip_locked=True)
            .all()
        )

        for turno in turnos:

            fecha_turno_aware_utc = timezone.ensure_utc(turno.fecha_hora)

            telefono = turno.usuario.telefonos[0].numero # o el que corresponda
            nombre_sucursal = auxiliares.nombre_empresa(turno.sucursal.empresa.nombre, turno.sucursal.nombre)
            cuando = formatear_fecha_hora_turno(fecha_turno_aware_utc, ahora_aware_utc)

            try:
                resultado = mensajes.enviar_sms(telefono, f'Recordatorio: tenés un turno en {nombre_sucursal} para {cuando}')

                if resultado:
                    turno.recordatorio_enviado = True
                    db.commit()

            except Exception as e:
                db.rollback()
    finally:
        db.close()

def limpiar_tokens_expirados():
    db = SessionLocal()
    try:
        ahora_utc = timezone.to_naive_utc(timezone.now_utc())
        db.query(models.Blacklist).filter(models.Blacklist.expires_at < ahora_utc).delete()
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
# Rehacer función ya que ya no existe más la tabla Historial

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