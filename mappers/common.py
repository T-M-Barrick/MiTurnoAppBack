from core import models, timezone
from schemas import common as schemas_common

def telefonos(telefonos: list[models.Telefono]) -> list[schemas_common.TelefonoConID]:
    return [schemas_common.TelefonoConID(id=t.id, numero=t.numero) for t in telefonos]

def direccion_out(direccion: models.Direccion) -> schemas_common.DireccionOut:
    return schemas_common.DireccionOut(
        id=direccion.id,
        calle=direccion.calle,
        altura=direccion.altura,
        localidad=direccion.localidad,
        departamento=direccion.departamento,
        provincia=direccion.provincia,
        pais=direccion.pais,
        lat=direccion.lat,
        lng=direccion.lng,
        aclaracion=direccion.aclaracion,
    )

def miembro_out(miembro: models.Miembro_Empresa | models.Miembro_Sucursal) -> schemas_common.MiembroOut:

    miembro_out = schemas_common.MiembroOut(
        id=miembro.usuario.id,
        dni=miembro.usuario.dni,
        apellido=miembro.usuario.apellido,
        nombre=miembro.usuario.nombre,
        email=miembro.usuario.email,
    )

    return miembro_out

def notificacion_out(notif: models.Notificacion) -> schemas_common.NotificacionOut:

    notificacion = schemas_common.NotificacionOut(
        id=notif.id,
        tipo=notif.tipo,
        extra_data=notif.extra_data,
        created_at=timezone.ensure_utc(notif.created_at),
        leida=notif.leida,
    )

    return notificacion

def notificaciones_out(
    notificaciones: list[models.Notificacion],
    ultimo_cursor_id: int | None
) -> schemas_common.NotificacionesOut:

    notificaciones = [notificacion_out(notif) for notif in notificaciones]
    
    respuesta = schemas_common.NotificacionesOut(
        notificaciones=notificaciones,
        ultimo_cursor_id=ultimo_cursor_id, # el campo ultimo_cursor_id volverá si la sucursal pide más notificaciones
    )

    return respuesta