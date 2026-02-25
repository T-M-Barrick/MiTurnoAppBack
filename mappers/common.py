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
        aclaracion=direccion.aclaracion)

def disponibilidad_servicio(disponibilidad):
    return schemas_common.DisponibilidadServicio(
        dia=disponibilidad.dia,
        hora_inicio=disponibilidad.hora_inicio,
        hora_fin=disponibilidad.hora_fin,
        intervalo=disponibilidad.intervalo,
        cant_turnos_max=disponibilidad.cant_turnos_max)

def miembro_out(miembro):

    miembro_out = schemas_common.MiembroOut(
        id=miembro.usuario.id,
        dni=miembro.usuario.dni,
        apellido=miembro.usuario.apellido,
        nombre=miembro.usuario.nombre,
        email=miembro.usuario.email)

    return miembro_out