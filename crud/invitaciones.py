from datetime import timedelta

from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import (
    get_empresa,
    get_sucursal,
    verificar_rol_en_empresa,
    verificar_rol_en_sucursal,
    verificar_rol_en_empresa_o_sucursal,
)
from core import models, constantes, exceptions, config, autenticacion, auxiliares,  mensajes

def invitar_empleado(db: Session, empresa_id: int,
    sucursal_id: int | None, current_user_id: int, usuario_email: str, invitacion_rol: str):

    if sucursal_id:
        sucursal = get_sucursal(db, sucursal_id)

        current_user_rol = verificar_rol_en_empresa_o_sucursal(db, current_user_id, sucursal.empresa.id, sucursal_id)

        if current_user_rol == 'EMPLEADO':
            raise exceptions.SucursalRolAssignedByEmpleadoError()

        if current_user_rol == 'GERENTE_SUCURSAL' and invitacion_rol == 'GERENTE_SUCURSAL':
            raise exceptions.SucursalRolAssignedByGerenteError()

    else:
        empresa = get_empresa(db, empresa_id)

        current_user_rol = verificar_rol_en_empresa(db, current_user_id, empresa_id)

        if current_user_rol != 'PROPIETARIO':
            raise exceptions.EmpresaRolNotAssignedByPropietarioError()
    
    # Buscar usuario por email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario_email).first()

    if not usuario:
        return None, None
    
    if not usuario.email_verificado:
        return None, None

    if sucursal_id:
        es_miembro = db.query(models.Miembro_Sucursal).filter_by(usuario_id=usuario.id, sucursal_id=sucursal_id).first()
        if es_miembro:
            raise exceptions.SucursalMiembroAlreadyExistsError()
        return usuario, sucursal
    else:
        es_miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario.id, empresa_id=empresa_id).first()
        if es_miembro:
            raise exceptions.EmpresaMiembroAlreadyExistsError()
        return usuario, empresa

    '''
    # Volver a poner si no se logra lo del mail
    ###################################
    db_invitacion_rol = auxiliares.get_rol_id(db, invitacion_rol, 'EMPRESA')

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
        sucursal_id = payload.get("sucursal_id")
        rol = payload.get("rol") # nombre del rol (como string, no como entero)
    except JWTError as e:
        raise exceptions.InvitationTokenInvalidExpiredError()
    
    # Buscar usuario por ID
    usuario = db.query(models.Usuario).filter_by(usuario_id=usuario_id).first()
    if not usuario:
        raise exceptions.UserNotFoundError()
    
    if empresa_id:

        roles_empresas = ['PROPIETARIO', 'GERENTE_EMPRESA']
        if rol not in roles_empresas:
            raise exceptions.InvitationTokenInvalidExpiredError()

        empresa = get_empresa(db, empresa_id)

        # Verificar si ya es miembro
        es_miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()
        if es_miembro:
            return empresa.nombre, rol

        db_rol_id = auxiliares.get_rol_id(db, rol, 'EMPRESA')
        
        nuevo_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol_id=db_rol_id)
    
    elif sucursal_id:

        roles_sucursales = ['GERENTE_SUCURSAL', 'EMPLEADO']
        if rol not in roles_sucursales:
            raise exceptions.InvitationTokenInvalidExpiredError()

        sucursal = get_sucursal(db, sucursal_id)

        # Verificar si ya es miembro
        es_miembro = db.query(models.Miembro_Sucursal).filter_by(usuario_id=usuario_id, sucursal_id=sucursal_id).first()
        if es_miembro:
            return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), rol
        
        db_rol_id = auxiliares.get_rol_id(db, rol, 'SUCURSAL')
        
        nuevo_miembro = models.Miembro_Sucursal(usuario_id=usuario_id, sucursal_id=sucursal_id, rol_id=db_rol_id)
    
    else:
        raise exceptions.InvitationTokenInvalidExpiredError()
    
    try:
        db.add(nuevo_miembro)
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    if empresa_id:
        return empresa.nombre, rol
    elif sucursal_id:
        return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), rol