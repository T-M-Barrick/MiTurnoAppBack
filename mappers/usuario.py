from mappers.common import telefonos, direccion_out, disponibilidad_servicio
from core import auxiliares, timezone
from core.constantes import Rol
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario

def base_usuario_dict(user):
    return dict(
        id=user.id,
        dni=user.dni,
        apellido=user.apellido,
        nombre=user.nombre,
        email=user.email,
        recordatorio=user.recordatorio_minutos_antes,
        telefonos=telefonos(user.telefonos),
        direcciones=[direccion_out(direccion) for direccion in user.direcciones]
    )

def empresa_out(empresa):
    return schemas_usuario.EmpresaOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        calificacion=empresa.calificacion,
        telefonos=[schemas_common.Telefono(numero=t.numero) for t in empresa.telefonos],
        direccion=direccion_out(empresa.direccion),
        logo_url=empresa.logo_url)

def turno_user_out(turno):
    tiene_profesional = turno.profesional_id != 1

    return schemas_usuario.TurnoUserOut(
        id=turno.id,
        empresa_id=turno.empresa_id,
        empresa=turno.empresa.nombre,
        logo_empresa_url=turno.empresa.logo_url,
        direccion=direccion_out(turno.empresa.direccion),
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        nombre_de_servicio=turno.nombre_de_servicio,
        duracion=turno.duracion,
        precio=turno.precio,
        aclaracion_de_servicio=turno.aclaracion_de_servicio,
        profesional_dni=turno.profesional.dni if tiene_profesional else None,
        profesional_apellido=turno.profesional.apellido if tiene_profesional else None,
        profesional_nombre=turno.profesional.nombre if tiene_profesional else None,
        estado_turno=turno.estado_turno_usuario.estado,
        recordatorio=turno.recordatorio_minutos_antes)

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioLoginOut de Pydantic (y agregándole turnos si tiene)
def user_login_out(user, turnos):
    data = base_usuario_dict(user)

    data["favoritos"] = [empresa_out(empresa) for empresa in user.favoritos]
    data["turnos"] = [turno_user_out(turno) for turno in turnos]

    return schemas_usuario.UserLoginOut(**data)

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioUpdateOut de Pydantic
def user_update_out(user):
    data = base_usuario_dict(user)

    return schemas_usuario.UserUpdateOut(**data)

def rol_empresa_out(miembro_empresa):
    return schemas_usuario.RolEmpresaOut(
        rol=Rol(miembro_empresa.rol).name,
        empresa_id=miembro_empresa.empresa_id,
        nombre_empresa=miembro_empresa.empresa.nombre,
        logo_empresa_url=miembro_empresa.empresa.logo_url,
        direccion=direccion_out(miembro_empresa.empresa.direccion)
    )

def turno_estado_out(turno):
    return schemas_common.TurnoEstadoOut(
        id=turno.id,
        estado=turno.estado_turno_usuario.estado)

def turno_historial_user(h):
    tiene_profesional = h.profesional_id != 1

    return schemas_usuario.TurnoHistorialUser(
        empresa=h.empresa.nombre,
        logo_empresa_url=h.empresa.logo_url,
        fecha_hora=timezone.ensure_utc(h.fecha_hora),
        nombre_de_servicio=h.nombre_de_servicio,
        duracion=h.duracion,
        precio=h.precio,
        aclaracion_de_servicio=h.aclaracion_de_servicio,
        profesional_dni=h.profesional.dni if tiene_profesional else None,
        profesional_apellido=h.profesional.apellido if tiene_profesional else None,
        profesional_nombre=h.profesional.nombre if tiene_profesional else None,
        estado_turno=h.estado_turno_usuario.estado if h.estado_turno_usuario else None)

def turno_actual_del_servicio(turno):
    return schemas_usuario.TurnoActualDelServicio(
        id=turno.id,
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        duracion=turno.duracion)

def servicio_con_turnos_out(servicios, turnos):

    turnos_por_servicio: dict[int, list[schemas_usuario.TurnoActualDelServicio]] = {}

    for t in turnos:
        turno_out = turno_actual_del_servicio(t)
        turnos_por_servicio.setdefault(t.servicio_id, []).append(turno_out)

    servicios_out = []

    for s in servicios:
        # Recorrer todas las disponibilidades asociadas
        disponibilidades_out = [disponibilidad_servicio(disponibilidad) for disponibilidad in s.disponibilidades]

        usuario = s.profesional if s.profesional_id != 1 else None

        servicio_out = schemas_usuario.ServicioConTurnosOut(
            id=s.id,
            nombre=s.nombre,
            duracion=s.duracion,
            precio=s.precio,
            aclaracion=s.aclaracion,
            profesional_id=s.profesional_id if usuario else None,
            profesional_dni=usuario.dni if usuario else None,
            profesional_apellido=usuario.apellido if usuario else None,
            profesional_nombre=usuario.nombre if usuario else None,
            dias_max_reserva=s.dias_max_reserva,
            disponibilidades=disponibilidades_out,
            turnos_actuales=turnos_por_servicio.get(s.id, []))

        servicios_out.append(servicio_out)

    return servicios_out