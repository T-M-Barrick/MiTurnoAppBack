from schemas import invitaciones as schemas_invitaciones

def invitacion_aceptada_out(
    entidad_nombre: str,
    nuevo_rol: str,
    cantidad_sucursales: int,
) -> schemas_invitaciones.InvitacionAceptadaOut:

    invitacion_out = schemas_invitaciones.InvitacionAceptadaOut(
        nombre=entidad_nombre,
        rol=nuevo_rol,
        cantidad_sucursales=cantidad_sucursales,
    )
    return invitacion_out