from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload, selectinload

from core import models, autenticacion, auxiliares, constantes, mensajes
from core.database import get_db
from schemas import invitaciones as schemas_invitaciones
from mappers import invitaciones as mappers_invitaciones

router = APIRouter(prefix="/invitaciones", tags=["Invitaciones"])

# {"message": f"Invitación enviada a {usuario_email} para el rol {rol}"}
@router.post("/empresas/{empresa_id}", status_code=204)
def invitar_empleado(
    empresa_id: int,
    invitacion: schemas_invitaciones.InvitacionEmpleadoIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    usuario_email = invitacion.usuario_email
    rol = invitacion.rol

    usuario_existe = crud_invitaciones.invitar_empleado(db, empresa_id, current_user.id, usuario_email, rol)

    if usuario_existe:
        # Crear token JWT usando create_access_token
        token = autenticacion.create_access_token(
            data={"usuario_id": usuario.id, "empresa_id": empresa_id, "rol": invitacion_rol},
            expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))

        # Enviar mail
        mensajes.send_invite_email(usuario_email, token, 
            empresa_nombre=empresa.nombre, rol=invitacion_rol)

    '''
    # Volver a poner si no se logra lo del mail
    ###################################
    from mappers import empresa as mappers_empresa

    nuevo_miembro = db.query(models.Usuario).filter_by(email=usuario_email).first()

    miembro = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario)).filter_by(
        usuario_id=nuevo_miembro.id, empresa_id=empresa_id).first()
    
    miembro_out = mappers_empresa.miembro_out(miembro)

    return miembro_out
    ###################################
    '''

# {"message": f"¡¡Fuiste incorporado exitosamente como {rol} para la empresa {empresa_nombre}!!"}
@router.post("/aceptar", response_model=schemas_invitaciones.InvitacionAceptadaOut, status_code=201)
def aceptar_invitacion(data: schemas_invitaciones.TokenRequest, db: Session = Depends(get_db)):

    empresa_nombre, nuevo_rol = crud_invitaciones.aceptar_invitacion(db, data.token)
    
    return mappers_invitaciones.invitacion_aceptada_out(empresa_nombre, nuevo_rol)