from datetime import timedelta

from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import get_empresa, verificar_rol_en_empresa
from core import models, constantes, exceptions, config, autenticacion, mensajes

def invitar_empleado(db: Session, empresa_id: int, current_user_id: int, usuario_email: str, invitacion_rol: str):

    empresa = get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, current_user_id, empresa_id)
    
    roles_superiores = ["propietario", "gerente"]

    if current_user_rol == 'gerente' and invitacion_rol in roles_superiores:
        raise exceptions.EmpresaRolAsignedByGerenteError()
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaRolAsignedByEmpleadoError()
    
    # Buscar usuario por email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario_email).first()

    if not usuario:
        return False
    
    if not usuario.email_verificado:
        return False
    
    es_miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario.id, empresa_id=empresa_id).first()
    if es_miembro:
        raise exceptions.EmpresaMiembroAlreadyExistsError()
    
    bloqueo = db.query(models.Empresa_Bloqueo).filter_by(empresa_id=empresa_id, usuario_id=usuario.id).first()
    if bloqueo:
        raise exceptions.InvitationUserBlockedError()
    
    return True

    '''
    # Volver a poner si no se logra lo del mail
    ###################################
    db_invitacion_rol = constantes.Rol[invitacion_rol].value

    try:
        nuevo_miembro = models.Miembro_Empresa(usuario_id=usuario.id, empresa_id=empresa_id, rol=db_invitacion_rol)
        db.add(nuevo_miembro)
        db.commit()
    except Exception:
        db.rollback()
        raise
    ###################################
    '''

def aceptar_invitacion(db: Session, token: str):

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        usuario_id = payload.get("usuario_id")
        empresa_id = payload.get("empresa_id")
        rol = payload.get("rol") # nombre del rol (como string, no como entero)
    except JWTError as e:
        raise exceptions.InvitationTokenInvalidExpiredError()
    
    # Buscar usuario por email
    usuario = db.query(models.Usuario).filter_by(usuario_id=usuario_id).first()
    if not usuario:
        raise exceptions.UserNotFoundError()
    
    empresa = get_empresa(db, empresa_id)

    # Verificar si ya es miembro
    es_miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()
    if es_miembro:
        return empresa.nombre, rol
    
    bloqueo = db.query(models.Empresa_Bloqueo).filter_by(empresa_id=empresa_id, usuario_id=usuario_id).first()
    if bloqueo:
        raise exceptions.InvitationError()

    db_rol = constantes.Rol[rol].value
    
    try:
        nuevo_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol=db_rol)
        db.add(nuevo_miembro)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return empresa.nombre, rol