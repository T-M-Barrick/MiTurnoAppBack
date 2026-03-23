from mappers.common import telefonos, direccion_out, servicio_out, excepcion_fecha_servicio_out, miembro_out, notificaciones_out
from core import auxiliares, timezone
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal

def sucursal_home_out(sucursal, notificaciones, ultimo_cursor_id, miembro_rol):
    
    sucursal_out = schemas_sucursal.SucursalHomeOut(
        id=sucursal.id,
        nombre_empresa=sucursal.empresa.nombre,
        nombre_sucursal=sucursal.nombre,
        logo_url=sucursal.empresa.logo_url,
        notificaciones=notificaciones_out(notificaciones, ultimo_cursor_id),
        rol=miembro_rol,
    )
    
    return sucursal_out

def sucursal_perfil_out(sucursal, miembro_rol):
    
    sucursal_out = schemas_sucursal.SucursalPerfilOut(
        id=sucursal.id,
        cuit=sucursal.empresa.cuit,
        nombre_empresa=sucursal.empresa.nombre,
        nombre_sucursal=sucursal.nombre,
        email_empresa=sucursal.empresa.email,
        email_sucursal=sucursal.email,
        reserva_publica_habilitada=sucursal.reserva_publica_habilitada,
        rubro=sucursal.empresa.rubro,
        rubro2=sucursal.empresa.rubro2,
        calificacion=sucursal.calificacion,
        telefonos=telefonos(sucursal.telefonos),
        direccion=direccion_out(sucursal.direccion),
        logo_url=sucursal.empresa.logo_url,
        rol=miembro_rol,
    )
    
    return sucursal_out

def cliente_out(cliente):

    return schemas_sucursal.ClienteOut(
        id=cliente.id,
        dni=cliente.dni,
        apellido=cliente.apellido,
        nombre=cliente.nombre,
        email=cliente.email,
        telefono=cliente.telefono,
        telefono2=cliente.telefono2,
        observacion=cliente.observacion,
        fecha_hora_alta=timezone.ensure_utc(cliente.fecha_hora_alta),
        activo=cliente.activo,
        bloqueado=cliente.bloqueo is not None,
    )

def turno_sucursal_out(turno):
    tiene_profesional = turno.profesional_id != None

    return schemas_sucursal.TurnoSucursalOut(
        id=turno.id,
        cliente_dni=turno.cliente.dni,
        cliente_apellido=turno.cliente.apellido,
        cliente_nombre=turno.cliente.nombre,
        cliente_email=turno.cliente.email,
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        servicio_id=turno.servicio_id,
        nombre_de_servicio=turno.nombre_de_servicio,
        duracion=turno.duracion,
        precio=turno.precio,
        aclaracion_de_servicio=turno.aclaracion_de_servicio,
        profesional_dni=turno.profesional.dni if tiene_profesional else None,
        profesional_apellido=turno.profesional.apellido if tiene_profesional else None,
        profesional_nombre=turno.profesional.nombre if tiene_profesional else None,
        created_at=timezone.ensure_utc(turno.created_at),
        estado_turno=turno.estado_turno_sucursal.estado,
    )

def turno_estado_out(turno):
    return schemas_common.TurnoEstadoOut(
        id=turno.id,
        estado=turno.estado_turno_sucursal.estado,
    )

def turno_historial_sucursal(h):
    tiene_profesional = h.profesional_id != None

    return schemas_sucursal.TurnoHistorialSucursal(
        cliente_dni=h.cliente.dni,
        cliente_apellido=h.cliente.apellido,
        cliente_nombre=h.cliente.nombre,
        cliente_email=h.cliente.email,
        fecha_hora=timezone.ensure_utc(h.fecha_hora),
        nombre_de_servicio=h.nombre_de_servicio,
        duracion=h.duracion,
        precio=h.precio,
        aclaracion_de_servicio=h.aclaracion_de_servicio,
        profesional_dni=h.profesional.dni if tiene_profesional else None,
        profesional_apellido=h.profesional.apellido if tiene_profesional else None,
        profesional_nombre=h.profesional.nombre if tiene_profesional else None,
        created_at=timezone.ensure_utc(h.created_at),
        estado_turno=h.estado_turno_sucursal.estado if h.estado_turno_sucursal else None,
    )

def servicio_sucursal_out(servicio_base):
    usuario = servicio_base.profesional if servicio_base.profesional_id != None else None

    servicio_out = schemas_sucursal.ServicioSucursalOut(
        id=servicio_base.id,
        nombre=servicio_base.nombre,
        aclaracion=servicio_base.aclaracion,
        profesional_id=servicio_base.profesional_id if usuario else None,
        profesional_dni=usuario.dni if usuario else None,
        profesional_apellido=usuario.apellido if usuario else None,
        profesional_nombre=usuario.nombre if usuario else None,
        minutos_min_reserva=servicio_base.minutos_min_reserva,
        dias_max_reserva=servicio_base.dias_max_reserva,
        cancelacion_limitada=servicio_base.cancelacion_limitada,
        servicios=[servicio_out(servicio) for servicio in servicio_base.servicios],
        excepciones_fechas=[excepcion_fecha_servicio_out(excepcion) for excepcion in servicio_base.excepciones_fechas],
    )

    return servicio_out

def miembro_sucursal_out(miembro):

    miembro_out = schemas_sucursal.MiembroSucursalOut(
        miembro=miembro_out(miembro),
        rol=miembro.rol.nombre,
    )

    return miembro_out

def block_cliente_out(bloqueo, miembro_rol):

    block_out = schemas_sucursal.BlockClienteOut(
        cliente=cliente_out(bloqueo.cliente),
        miembro_dni=bloqueo.usuario_bloqueador.dni,
        miembro_apellido=bloqueo.usuario_bloqueador.apellido,
        miembro_nombre=bloqueo.usuario_bloqueador.nombre,
        miembro_rol=miembro_rol,
        motivo=bloqueo.motivo,
        created_at=timezone.ensure_utc(bloqueo.created_at),
    )

    return block_out