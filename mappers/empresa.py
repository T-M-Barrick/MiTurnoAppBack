from mappers.common import telefonos, direccion_out, disponibilidad_servicio
from core import auxiliares, timezone
from core.constantes import Rol
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa

# Convierte un objeto de la clase Empresa de SQLAlchemy en uno de clase EmpresaHomeOut de Pydantic
def empresa_home_out(empresa, miembro_rol):

    empresa_out = schemas_empresa.EmpresaHomeOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        calificacion=empresa.calificacion,
        telefonos=telefonos(empresa.telefonos),
        direccion=direccion_out(empresa.direccion),
        logo_url=empresa.logo_url,
        rol=miembro_rol)

    return empresa_out

def empresa_logo_out(logo_url):
    return schemas_empresa.EmpresaLogoOut(logo_url=logo_url)

def turno_empresa_out(turno):
    tiene_profesional = turno.profesional_id != 1

    return schemas_empresa.TurnoEmpresaOut(
        id=turno.id,
        usuario_dni=turno.usuario.dni,
        usuario_apellido=turno.usuario.apellido,
        usuario_nombre=turno.usuario.nombre,
        usuario_email=turno.usuario.email,
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        servicio_id=turno.servicio_id,
        nombre_de_servicio=turno.nombre_de_servicio,
        duracion=turno.duracion,
        precio=turno.precio,
        aclaracion_de_servicio=turno.aclaracion_de_servicio,
        profesional_dni=turno.profesional.dni if tiene_profesional else None,
        profesional_apellido=turno.profesional.apellido if tiene_profesional else None,
        profesional_nombre=turno.profesional.nombre if tiene_profesional else None,
        estado_turno=turno.estado_turno_empresa.estado)

def turno_estado_out(turno):
    return schemas_common.TurnoEstadoOut(
        id=turno.id,
        estado=turno.estado_turno_empresa.estado)

def turno_historial_empresa(h):
    tiene_profesional = h.profesional_id != 1

    return schemas_empresa.TurnoHistorialEmpresa(
        usuario_dni=h.usuario.dni,
        usuario_apellido=h.usuario.apellido,
        usuario_nombre=h.usuario.nombre,
        usuario_email=h.usuario.email,
        fecha_hora=timezone.ensure_utc(h.fecha_hora),
        nombre_de_servicio=h.nombre_de_servicio,
        duracion=h.duracion,
        precio=h.precio,
        aclaracion_de_servicio=h.aclaracion_de_servicio,
        profesional_dni=h.profesional.dni if tiene_profesional else None,
        profesional_apellido=h.profesional.apellido if tiene_profesional else None,
        profesional_nombre=h.profesional.nombre if if tiene_profesional else None,
        estado_turno=h.estado_turno_empresa.estado if h.estado_turno_empresa else None)

def servicio_empresa_out(servicio):
    usuario = servicio.profesional if servicio.profesional_id != 1 else None

    servicio_out = schemas_empresa.ServicioEmpresaOut(
        id=servicio.id,
        nombre=servicio.nombre,
        duracion=servicio.duracion,
        precio=servicio.precio,
        aclaracion=servicio.aclaracion,
        profesional_id=servicio.profesional_id if usuario else None,
        profesional_dni=usuario.dni if usuario else None,
        profesional_apellido=usuario.apellido if usuario else None,
        profesional_nombre=usuario.nombre if usuario else None,
        minutos_min_reserva=servicio.minutos_min_reserva,
        dias_max_reserva=servicio.dias_max_reserva,
        cancelacion_limitada=servicio.cancelacion_limitada,
        disponibilidades=[disponibilidad_servicio(d) for d in servicio.disponibilidades]
    )

    return servicio_out

def miembro_out(miembro):

    miembro_out = schemas_empresa.MiembroOut(
        id=miembro.usuario.id,
        dni=miembro.usuario.dni,
        apellido=miembro.usuario.apellido,
        nombre=miembro.usuario.nombre,
        email=miembro.usuario.email,
        rol=Rol(miembro.rol).name)

    return miembro_out

def rol_out(rol): # rol es el nombre del rol, no el entero

    return schemas_empresa.RolOut(rol=rol)

def block_user_out(bloqueo, miembro_rol):

    block_user_out = schemas_empresa.BlockUserOut(
        usuario_email=bloqueo.usuario.email,
        miembro_dni=bloqueo.usuario_bloqueador.dni,
        miembro_apellido=bloqueo.usuario_bloqueador.apellido,
        miembro_nombre=bloqueo.usuario_bloqueador.nombre,
        miembro_rol=miembro_rol,
        motivo=bloqueo.motivo,
        created_at=timezone.ensure_utc(bloqueo.created_at)
    )

    return block_user_out