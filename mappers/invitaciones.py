from schemas import invitaciones as schemas_invitaciones

def invitacion_aceptada_out(empresa_nombre, nuevo_rol):
    return schemas_invitaciones.InvitacionAceptadaOut(
        empresa=empresa_nombre,
        rol=nuevo_rol)