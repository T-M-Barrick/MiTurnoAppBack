from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from core.database import SessionLocal
from core import models, mensajes, auxiliares, timezone

def enviar_recordatorios() -> None:
    db = SessionLocal()

    ahora_aware_utc = timezone.now_utc() # aware UTC
    ahora_naive_utc = timezone.to_naive_utc(ahora_aware_utc) # naive UTC (DB)

    try:
        while True:
            # Buscar turnos cuyo recordatorio debe enviarse AHORA
            try:
                turno = (
                    db.query(models.Turno)
                    .options(
                        joinedload(models.Turno.usuario).selectinload(models.Usuario.telefonos),
                        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.empresa),
                    )
                    .filter(
                        models.Turno.recordatorio_enviado == False,
                        models.Turno.estado_turno_usuario_id == 1, # esto evita enviar recordatorios de turnos cancelados
                        models.Turno.recordatorio_fecha_hora.isnot(None),
                        models.Turno.recordatorio_fecha_hora <= ahora_naive_utc,
                        models.Turno.eliminado_por_usuario == False,
                        models.Turno.fecha_hora > ahora_naive_utc,
                    )
                    # Con with_for_update(skip_locked=True) las filas seleccionadas quedan bloqueadas y
                    # si otro worker ya las bloqueó, las salta y así evito enviar el mismo SMS dos veces en paralelo
                    .with_for_update(of=models.Turno, skip_locked=True)
                    .first()
                )

                if not turno:
                    break

                fecha_turno_aware_utc = timezone.ensure_utc(turno.fecha_hora)

                if not turno.usuario.telefonos:
                    db.commit()
                    continue

                telefono = turno.usuario.telefonos[0].numero # o el que corresponda
                nombre_sucursal = auxiliares.nombre_empresa(turno.sucursal.empresa.nombre, turno.sucursal.nombre)
                cuando = auxiliares.formatear_fecha_hora_turno(fecha_turno_aware_utc)

                resultado = mensajes.enviar_sms(telefono, f'Recordatorio: tenés un turno en {nombre_sucursal} para {cuando}')

                if resultado:
                    turno.recordatorio_enviado = True

                db.commit()
            except Exception:
                db.rollback()

    finally:
        db.close()

def limpiar_turnos_a_historial() -> None:
    db = SessionLocal()

    ahora_naive_utc = timezone.to_naive_utc(timezone.now_utc())
    limite = ahora_naive_utc - timedelta(days=180)

    try:
        db.query(models.Turno).filter(
            models.Turno.fecha_hora < limite,
            or_(
                models.Turno.eliminado_por_usuario == False,
                models.Turno.eliminado_por_sucursal == False,
            ),
            models.Turno.estado_turno_usuario_id != 1,
            models.Turno.estado_turno_sucursal_id != 1,
        ).update(
            {
                models.Turno.eliminado_por_usuario: True,
                models.Turno.eliminado_por_sucursal: True,
            },
            synchronize_session=False
        )

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def limpiar_notificaciones_viejas() -> None:
    db = SessionLocal()

    try:
        ahora_naive_utc = timezone.to_naive_utc(timezone.now_utc())

        limite_leidas = ahora_naive_utc - timedelta(days=90) # datetime naive UTC
        limite_no_leidas = ahora_naive_utc - timedelta(days=365) # datetime naive UTC

        db.query(models.Notificacion).filter(
            models.Notificacion.leida == True,
            models.Notificacion.created_at < limite_leidas,
        ).delete(synchronize_session=False)

        db.query(models.Notificacion).filter(
            models.Notificacion.leida == False,
            models.Notificacion.created_at < limite_no_leidas,
        ).delete(synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def limpiar_tokens_expirados() -> None:
    db = SessionLocal()
    try:
        ahora_naive_utc = timezone.to_naive_utc(timezone.now_utc())
        db.query(models.Blacklist).filter(models.Blacklist.expires_at < ahora_naive_utc).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def start_scheduler() -> None:
    scheduler = BackgroundScheduler()
    'scheduler.add_job(enviar_recordatorios, "cron", minute="0,5,10,15,20,25,30,35,40,45,50,55")'
    scheduler.add_job(limpiar_turnos_a_historial, "interval", hours=24)
    scheduler.add_job(limpiar_notificaciones_viejas, "interval", hours=24)
    scheduler.add_job(limpiar_tokens_expirados, "interval", hours=24)
    scheduler.start()