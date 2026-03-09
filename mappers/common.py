from schemas import common as schemas_common

def telefonos(telefonos):
    return [schemas_common.TelefonoConID(id=t.id, numero=t.numero) for t in telefonos]

def direccion_out(direccion):
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

def disponibilidad_servicio(disponibilidad):
    return schemas_common.DisponibilidadServicio(
        dia=disponibilidad.dia,
        hora_inicio=disponibilidad.hora_inicio,
        hora_fin=disponibilidad.hora_fin,
        intervalo=disponibilidad.intervalo,
        cant_turnos_max=disponibilidad.cant_turnos_max,
    )

def servicio_out(servicio):

    servicio = schemas_common.ServicioOut(
        id=servicio.id,
        servicio_base_id=servicio.servicio_base_id,
        duracion=servicio.duracion,
        precio=servicio.precio,
        vigente_desde=servicio.vigente_desde,
        vigente_hasta=servicio.vigente_hasta,
        created_at=servicio.created_at,
        modify_at=servicio.modify_at,
        disponibilidades=[disponibilidad_servicio(d) for d in servicio.disponibilidades],
    )

    return servicio

def excepcion_fecha_servicio_out(excepcion):

    excepcion_out = schemas_common.ExcepcionFechaServicioOut(
        id=excepcion.id,
        fecha_inicio=excepcion.fecha_inicio,
        fecha_fin=excepcion.fecha_fin,
        motivo=excepcion.motivo,
    )

    return excepcion_out

def miembro_out(miembro):

    miembro_out = schemas_common.MiembroOut(
        id=miembro.usuario.id,
        dni=miembro.usuario.dni,
        apellido=miembro.usuario.apellido,
        nombre=miembro.usuario.nombre,
        email=miembro.usuario.email,
    )

    return miembro_out

def notificacion_out(notif):

    notificacion = schemas_common.NotificacionOut(
        id=notif.id,
        tipo=notif.tipo,
        extra_data=notif.extra_data,
        created_at=notif.created_at,
        leida=notif.leida,
    )

    return notificacion

def notificaciones_out(notificaciones, ultimo_cursor_id):

    notificaciones = [notificacion_out(notif) for notif in notificaciones]
    
    respuesta = schemas_common.NotificacionesOut(
        notificaciones=notificaciones,
        ultimo_cursor_id=ultimo_cursor_id, # el campo ultimo_cursor_id volverá si la sucursal pide más notificaciones
    )

    return respuesta