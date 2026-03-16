from datetime import timedelta

from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import (
    get_empresa,
    get_sucursal,
    verificar_rol_en_empresa,
    verificar_rol_en_sucursal,
    verificar_rol_en_empresa_o_sucursal,
    crear_extra_data_notificacion,
    guardar_notificacion,
)
from core import models, constantes, exceptions, config, autenticacion, auxiliares,  mensajes

def invitar_empleado(db: Session, empresa_id: int,
    sucursal_id: int | None, current_user_id: int, usuario_email: str, invitacion_rol: str):

    empresa = get_empresa(db, empresa_id)

    if sucursal_id:
        sucursal = get_sucursal(db, sucursal_id)

        if sucursal.empresa_id != empresa_id:
            raise exceptions.SucursalNotFoundError()

        current_user_rol = verificar_rol_en_empresa_o_sucursal(db, current_user_id, sucursal.empresa.id, sucursal_id)

        if current_user_rol == 'EMPLEADO':
            raise exceptions.SucursalRolAssignedByEmpleadoError()

        if current_user_rol == 'GERENTE_SUCURSAL' and invitacion_rol == 'GERENTE_SUCURSAL':
            raise exceptions.SucursalRolAssignedByGerenteError()

    else:
        current_user_rol = verificar_rol_en_empresa(db, current_user_id, empresa_id)

        if current_user_rol != 'PROPIETARIO':
            raise exceptions.EmpresaRolNotAssignedByPropietarioError()
    
    # Buscar usuario por email
    email_normalizado = models.normalizar_email(usuario_email)
    usuario = db.query(models.Usuario).filter(models.Usuario.email_normalizado == email_normalizado).first()

    if not usuario:
        return None, None
    
    if not usuario.email_verificado:
        return None, None
    
    # Verificar si ya es miembro de la empresa (rol global)
    es_miembro = db.query(models.Miembro_Empresa.id).filter_by(
        usuario_id=usuario.id,
        empresa_id=empresa_id,
    ).first()

    if es_miembro:
        raise exceptions.EmpresaMiembroAlreadyExistsError()
    
    if sucursal_id:
        # Verificar si ya es miembro de la sucursal
        es_miembro = db.query(models.Miembro_Sucursal.id).filter_by(
            usuario_id=usuario.id,
            sucursal_id=sucursal_id
        ).first()

        if es_miembro:
            raise exceptions.SucursalMiembroAlreadyExistsError()

    else:
        # Verificar si ya es miembro de alguna sucursal de la empresa
        es_miembro = (
            db.query(models.Miembro_Sucursal)
            .join(models.Sucursal)
            .filter(
                models.Miembro_Sucursal.usuario_id == usuario.id,
                models.Sucursal.empresa_id == empresa_id
            )
            .first()
        )

        if es_miembro:
            sucursal = next((s for s in empresa.sucursales if s.id == es_miembro.sucursal_id), None)
            if sucursal:
                raise exceptions.EmpresaMiembroAlreadyExistsInAnySucursalError(nombre_sucursal=sucursal.nombre)

    if sucursal_id:
        return usuario, sucursal
    else:
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

# Las notificaciones siempre se envian a miembros con roles iguales o inferiores al rol que se desea asignar
# (con excepciones de los empleados que no reciben notificación)
def aceptar_invitacion(db: Session, token: str):

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        usuario_id = payload.get("usuario_id")
        empresa_id = payload.get("empresa_id")
        sucursal_id = payload.get("sucursal_id")
        rol = payload.get("rol") # nombre del rol (como string, no como entero)
    except JWTError as e:
        raise exceptions.InvitationTokenInvalidExpiredError()
    
    empresa = get_empresa(db, empresa_id)
    
    # Buscar usuario por ID
    usuario = db.query(models.Usuario).filter_by(id=usuario_id).first()
    if not usuario:
        raise exceptions.UserNotFoundError()
    
    try:
        miembros_de_la_empresa = db.query(models.Miembro_Empresa).options(
            joinedload(models.Miembro_Empresa.rol),
        ).filter(
            models.Miembro_Empresa.empresa_id == empresa_id,
        ).order_by(models.Miembro_Empresa.id.asc()).with_for_update(of=models.Miembro_Empresa).all()
        
        # Verificar si ya es miembro de la empresa (rol global)
        es_miembro = next((m_e.usuario_id == usuario_id for m_e in miembros_de_la_empresa), None)
        if es_miembro:
            return empresa.nombre, es_miembro.rol.nombre
        
        if sucursal_id:
            sucursal = get_sucursal(db, sucursal_id)

            if sucursal.empresa_id != empresa_id:
                raise exceptions.SucursalNotFoundError()

            miembros_de_la_sucursal = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.rol),
            ).filter(
                models.Miembro_Sucursal.sucursal_id == sucursal_id,
            ).order_by(models.Miembro_Sucursal.id.asc()).with_for_update(of=models.Miembro_Sucursal).all()

            # Verificar si ya es miembro de la sucursal
            es_miembro = next((m_s.usuario_id == usuario_id for m_s in miembros_de_la_sucursal), None)
            if es_miembro:
                return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), es_miembro.rol.nombre

        else:
            # Verificar si ya es miembro de alguna sucursal de la empresa
            es_miembro = (
                db.query(models.Miembro_Sucursal)
                .join(models.Sucursal)
                .options(joinedload(models.Miembro_Sucursal.rol))
                .filter(
                    models.Miembro_Sucursal.usuario_id == usuario_id,
                    models.Sucursal.empresa_id == empresa_id
                )
                .first()
            )

            if es_miembro:
                sucursal = next((s for s in empresa.sucursales if s.id == es_miembro.sucursal_id), None)
                if sucursal:
                    return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), es_miembro.rol.nombre

        if sucursal_id:

            roles_sucursales = ['GERENTE_SUCURSAL', 'EMPLEADO']
            if rol not in roles_sucursales:
                raise exceptions.InvitationTokenInvalidExpiredError()
            
            db_rol_id = auxiliares.get_rol_id(db, rol, 'SUCURSAL')
            
            nuevo_miembro = models.Miembro_Sucursal(usuario_id=usuario_id, sucursal_id=sucursal_id, rol_id=db_rol_id)

            extra_data = crear_extra_data_notificacion(
                usuario_id=usuario_id,
                usuario_apellido=usuario.apellido,
                usuario_nombre=usuario.nombre,
                nombre_sucursal=sucursal.nombre,
                rol=rol,
            )
            for m_e in miembros_de_la_empresa:
                if auxiliares.rol_superior(rol, m_e.rol.nombre):
                    continue
                guardar_notificacion(db, m_e.usuario_id, "MIEMBRO_NUEVO_SUCURSAL", extra_data, empresa_id=empresa_id)

            extra_data = crear_extra_data_notificacion(
                usuario_id=usuario_id,
                usuario_apellido=usuario.apellido,
                usuario_nombre=usuario.nombre,
                rol=rol,
            )
            for m_s in miembros_de_la_sucursal:
                if m_s.rol.nombre == 'EMPLEADO':
                    continue
                if auxiliares.rol_superior(rol, m_s.rol.nombre):
                    continue
                guardar_notificacion(db, m_s.usuario_id, "MIEMBRO_NUEVO_SUCURSAL", extra_data, sucursal_id=sucursal_id)
        
        else:

            roles_empresas = ['PROPIETARIO', 'GERENTE_EMPRESA']
            if rol not in roles_empresas:
                raise exceptions.InvitationTokenInvalidExpiredError()

            db_rol_id = auxiliares.get_rol_id(db, rol, 'EMPRESA')
            
            nuevo_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol_id=db_rol_id)

            extra_data = crear_extra_data_notificacion(
                usuario_id=usuario_id,
                usuario_apellido=usuario.apellido,
                usuario_nombre=usuario.nombre,
                rol=rol,
            )
            for m_e in miembros_de_la_empresa:
                guardar_notificacion(db, m_e.usuario_id, "MIEMBRO_NUEVO_EMPRESA", extra_data, empresa_id=empresa_id)
    
        db.add(nuevo_miembro)
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    if sucursal_id:
        return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), rol
    else:
        return empresa.nombre, rol