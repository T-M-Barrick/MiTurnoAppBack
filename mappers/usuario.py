from mappers.common import telefonos, direccion_out, notificaciones_out
from core import models, auxiliares, timezone
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario

def base_usuario_dict(user: models.Usuario) -> dict:
    return dict(
        id=user.id,
        dni=user.dni,
        apellido=user.apellido,
        nombre=user.nombre,
        email=user.email,
        recordatorio_minutos_antes=user.recordatorio_minutos_antes,
        telefonos=telefonos(user.telefonos),
        direcciones=[direccion_out(direccion) for direccion in user.direcciones],
    )

def sucursal_out(sucursal: models.Sucursal) -> schemas_usuario.SucursalOut:
    return schemas_usuario.SucursalOut(
        id=sucursal.id,
        cuit=sucursal.empresa.cuit,
        nombre=auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre),
        email=sucursal.email if sucursal.email else sucursal.empresa.email,
        rubro=sucursal.empresa.rubro,
        rubro2=sucursal.empresa.rubro2,
        calificacion=sucursal.calificacion,
        telefonos=[schemas_common.Telefono(numero=t.numero) for t in sucursal.telefonos],
        direccion=direccion_out(sucursal.direccion),
        logo_url=sucursal.empresa.logo_url,
    )

def turno_user_out(turno: models.Turno) -> schemas_usuario.TurnoUserOut:
    tiene_profesional = turno.profesional_id != None

    if turno.recordatorio_fecha_hora is not None:
        delta = turno.fecha_hora - turno.recordatorio_fecha_hora
        minutos_antes = int(delta.total_seconds() / 60)
    else:
        minutos_antes = None

    return schemas_usuario.TurnoUserOut(
        id=turno.id,
        sucursal_id=turno.sucursal_id,
        sucursal=auxiliares.nombre_empresa(turno.sucursal.empresa.nombre, turno.sucursal.nombre),
        logo_empresa_url=turno.sucursal.empresa.logo_url,
        direccion=direccion_out(turno.sucursal.direccion),
        fecha_hora=timezone.ensure_utc(turno.fecha_hora),
        nombre_de_servicio=turno.nombre_de_servicio,
        duracion=turno.duracion,
        precio=turno.precio,
        aclaracion_de_servicio=turno.aclaracion_de_servicio,
        profesional_dni=turno.profesional.dni if tiene_profesional else None,
        profesional_apellido=turno.profesional.apellido if tiene_profesional else None,
        profesional_nombre=turno.profesional.nombre if tiene_profesional else None,
        created_at=timezone.ensure_utc(turno.created_at),
        estado_turno=turno.estado_turno_usuario.estado,
        recordatorio_minutos_antes=minutos_antes,
    )

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioLoginOut de Pydantic
def user_login_out(
    user: models.Usuario,
    turnos: list[models.Turno],
    notificaciones: list[models.Notificacion],
    ultimo_cursor_id: int | None,
) -> schemas_usuario.UserLoginOut:

    data = base_usuario_dict(user)

    data["favoritos"] = [sucursal_out(sucursal) for sucursal in user.favoritos]
    data["turnos"] = [turno_user_out(turno) for turno in turnos]
    data["notificaciones"] = notificaciones_out(notificaciones, ultimo_cursor_id)

    return schemas_usuario.UserLoginOut(**data)

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioUpdateOut de Pydantic
def user_update_out(user: models.Usuario) -> schemas_usuario.UserUpdateOut:
    data = base_usuario_dict(user)

    return schemas_usuario.UserUpdateOut(**data)

def rol_empresa_out(miembro_empresa: models.Miembro_Empresa) -> schemas_usuario.RolEmpresaOut:
    return schemas_usuario.RolEmpresaOut(
        empresa_id=miembro_empresa.empresa_id,
        nombre_empresa=miembro_empresa.empresa.nombre,
        logo_empresa_url=miembro_empresa.empresa.logo_url,
        email=miembro_empresa.empresa.email,
        rol=miembro_empresa.rol.nombre,
    )

def rol_sucursal_out(miembro_sucursal: models.Miembro_Sucursal) -> schemas_usuario.RolSucursalOut:
    return schemas_usuario.RolSucursalOut(
        sucursal_id=miembro_sucursal.sucursal_id,
        nombre_sucursal=auxiliares.nombre_empresa(miembro_sucursal.sucursal.empresa.nombre, miembro_sucursal.sucursal.nombre),
        logo_empresa_url=miembro_sucursal.sucursal.empresa.logo_url,
        email=miembro_sucursal.sucursal.email if miembro_sucursal.sucursal.email else miembro_sucursal.sucursal.empresa.email,
        rol=miembro_sucursal.rol.nombre,
    )

def mis_empresas_out(
    miembro_empresas: list[models.Miembro_Empresa],
    miembro_sucursales: list[models.Miembro_Sucursal],
) -> schemas_usuario.MisEmpresasOut:

    empresas = schemas_usuario.MisEmpresasOut(
        empresas=[rol_empresa_out(m_e) for m_e in miembro_empresas],
        sucursales=[rol_sucursal_out(m_s) for m_s in miembro_sucursales],
    )

    return empresas

def turno_estado_out(turno: models.Turno) -> schemas_common.TurnoEstadoOut:
    return schemas_common.TurnoEstadoOut(
        id=turno.id,
        estado=turno.estado_turno_usuario.estado,
    )

def turno_historial_user(h: models.Turno) -> schemas_usuario.TurnoHistorialUser:
    tiene_profesional = h.profesional_id != None

    return schemas_usuario.TurnoHistorialUser(
        id=h.id,
        sucursal=auxiliares.nombre_empresa(h.sucursal.empresa.nombre, h.sucursal.nombre),
        logo_empresa_url=h.sucursal.empresa.logo_url,
        fecha_hora=timezone.ensure_utc(h.fecha_hora),
        nombre_de_servicio=h.nombre_de_servicio,
        duracion=h.duracion,
        precio=h.precio,
        aclaracion_de_servicio=h.aclaracion_de_servicio,
        profesional_dni=h.profesional.dni if tiene_profesional else None,
        profesional_apellido=h.profesional.apellido if tiene_profesional else None,
        profesional_nombre=h.profesional.nombre if tiene_profesional else None,
        created_at=timezone.ensure_utc(h.created_at),
        estado_turno=h.estado_turno_usuario.estado if h.estado_turno_usuario else None,
    )