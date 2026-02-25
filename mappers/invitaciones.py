from schemas import invitaciones as schemas_invitaciones

def invitacion_aceptada_out(entidad_nombre, nuevo_rol):
    return schemas_invitaciones.InvitacionAceptadaOut(
        nombre=entidad_nombre,
        rol=nuevo_rol)