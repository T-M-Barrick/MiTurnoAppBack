from mappers.common import telefonos, direccion_out, miembro_out, notificaciones_out
from core import models, timezone
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal

def sucursal_home_out(
    sucursal: models.Sucursal,
    notificaciones: list[models.Notificacion],
    ultimo_cursor_id: int | None,
    miembro_rol: str,
    cantidad_sucursales: int,
) -> schemas_sucursal.SucursalHomeOut:
    
    sucursal_out = schemas_sucursal.SucursalHomeOut(
        id=sucursal.id,
        empresa_id=sucursal.empresa_id,
        nombre_empresa=sucursal.empresa.nombre,
        nombre_sucursal=sucursal.nombre,
        logo_url=sucursal.empresa.logo_url,
        notificaciones=notificaciones_out(notificaciones, ultimo_cursor_id),
        rol=miembro_rol,
        cantidad_sucursales=cantidad_sucursales,
    )
    
    return sucursal_out

def sucursal_perfil_out(sucursal: models.Sucursal) -> schemas_sucursal.SucursalPerfilOut:
    
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
    )
    
    return sucursal_out

def cliente_out(cliente: models.Cliente) -> schemas_sucursal.ClienteOut:

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

def turno_sucursal_out(turno: models.Turno) -> schemas_sucursal.TurnoSucursalOut:
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

def turno_estado_out(turno: models.Turno) -> schemas_common.TurnoEstadoOut:
    return schemas_common.TurnoEstadoOut(
        id=turno.id,
        estado=turno.estado_turno_sucursal.estado,
    )

def turno_historial_sucursal(h: models.Turno) -> schemas_sucursal.TurnoHistorialSucursal:
    tiene_profesional = h.profesional_id != None

    return schemas_sucursal.TurnoHistorialSucursal(
        id=h.id,
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

def disponibilidad_servicio(disponibilidad: models.Disponibilidad) -> schemas_sucursal.DisponibilidadServicio:
    return schemas_sucursal.DisponibilidadServicio(
        dia=disponibilidad.dia,
        hora_inicio=disponibilidad.hora_inicio,
        hora_fin=disponibilidad.hora_fin,
        intervalo=disponibilidad.intervalo,
        cant_turnos_max=disponibilidad.cant_turnos_max,
    )

def servicio_out(servicio: models.Servicio) -> schemas_sucursal.ServicioOut:

    servicio = schemas_sucursal.ServicioOut(
        id=servicio.id,
        servicio_base_id=servicio.servicio_base_id,
        duracion=servicio.duracion,
        precio=servicio.precio,
        vigente_desde=servicio.vigente_desde,
        vigente_hasta=servicio.vigente_hasta,
        created_at=timezone.ensure_utc(servicio.created_at),
        modify_at=timezone.ensure_utc(servicio.modify_at) if servicio.modify_at else None,
        disponibilidades=[disponibilidad_servicio(d) for d in servicio.disponibilidades],
    )

    return servicio

def excepcion_fecha_servicio_out(excepcion: models.ExcepcionFechaServicio) -> schemas_sucursal.ExcepcionFechaServicioOut:

    excepcion_out = schemas_sucursal.ExcepcionFechaServicioOut(
        id=excepcion.id,
        fecha_inicio=excepcion.fecha_inicio,
        fecha_fin=excepcion.fecha_fin,
        motivo=excepcion.motivo,
    )

    return excepcion_out

def servicio_base_out(servicio_base: models.ServicioBase) -> schemas_sucursal.ServicioBaseOut:
    usuario = servicio_base.profesional if servicio_base.profesional_id != None else None

    out = schemas_sucursal.ServicioBaseOut(
        id=servicio_base.id,
        nombre=servicio_base.nombre,
        aclaracion=servicio_base.aclaracion,
        profesional_id=servicio_base.profesional_id if usuario else None,
        profesional_dni=usuario.dni if usuario else None,
        profesional_apellido=usuario.apellido if usuario else None,
        profesional_nombre=usuario.nombre if usuario else None,
        minutos_minimos_anticipacion_reserva=servicio_base.minutos_minimos_anticipacion_reserva,
        limite_dias_reserva=servicio_base.limite_dias_reserva,
        cancelacion_turno_limitada=servicio_base.cancelacion_turno_limitada,
        servicios=[servicio_out(servicio) for servicio in servicio_base.servicios],
        excepciones_fechas=[excepcion_fecha_servicio_out(excepcion) for excepcion in servicio_base.excepciones_fechas],
    )

    return out

def turno_actual_del_servicio(turno: models.Turno) -> schemas_sucursal.TurnoActualDelServicio:
    return schemas_sucursal.TurnoActualDelServicio(
        id=turno.id,
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        duracion=turno.duracion,
    )

def servicio_base_para_reserva_out(
    servicio_base: models.ServicioBase,
    turnos_actuales: list[schemas_sucursal.TurnoActualDelServicio],
) -> schemas_sucursal.ServicioBaseParaReservaOut:

    usuario = servicio_base.profesional if servicio_base.profesional_id != None else None

    out = schemas_sucursal.ServicioBaseParaReservaOut(
        id=servicio_base.id,
        nombre=servicio_base.nombre,
        aclaracion=servicio_base.aclaracion,
        profesional_id=servicio_base.profesional_id if usuario else None,
        profesional_dni=usuario.dni if usuario else None,
        profesional_apellido=usuario.apellido if usuario else None,
        profesional_nombre=usuario.nombre if usuario else None,
        limite_dias_reserva=servicio_base.limite_dias_reserva,
        servicios=[servicio_out(servicio) for servicio in servicio_base.servicios],
        turnos_actuales=turnos_actuales,
        excepciones_fechas=[excepcion_fecha_servicio_out(excepcion) for excepcion in servicio_base.excepciones_fechas],
    )

    return out

def lista_servicio_base_para_reserva_out(
    servicios_base: list[models.ServicioBase],
    turnos: list[models.Turno],
) -> list[schemas_sucursal.ServicioBaseParaReservaOut]:

    turnos_por_servicio_base: dict[int, list[schemas_sucursal.TurnoActualDelServicio]] = {}

    servicio_base_map = {}

    for servicio_base in servicios_base:
        for servicio in servicio_base.servicios:
            servicio_base_map[servicio.id] = servicio_base.id
    
    for t in turnos:
        turno_out = turno_actual_del_servicio(t)

        servicio_base_id = servicio_base_map.get(t.servicio_id)

        if servicio_base_id:
            turnos_por_servicio_base.setdefault(servicio_base_id, []).append(turno_out)

    servicios_out = []

    for servicio_base in servicios_base:

        servicio_out = servicio_base_para_reserva_out(
            servicio_base,
            turnos_por_servicio_base.get(servicio_base.id, []),
        )

        servicios_out.append(servicio_out)

    return servicios_out

def miembro_sucursal_out(miembro: models.Miembro_Sucursal) -> schemas_sucursal.MiembroSucursalOut:

    out = schemas_sucursal.MiembroSucursalOut(
        miembro=miembro_out(miembro),
        rol=miembro.rol.nombre,
    )

    return out

def block_cliente_out(bloqueo: models.BloqueoSucursal, miembro_rol: str) -> schemas_sucursal.BlockClienteOut:

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