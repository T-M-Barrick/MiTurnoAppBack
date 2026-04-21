from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import (
    get_empresa,
    get_sucursal,
    verificar_rol_en_empresa,
    verificar_rol_en_empresa_o_sucursal,
    crear_extra_data_notificacion,
    guardar_notificacion,
)
from core import models, exceptions, config, auxiliares

def invitar_empleado(
    db: Session,
    empresa_id: int,
    sucursal_id: int | None,
    current_user_id: int,
    usuario_email: str,
    invitacion_rol: str,
) -> tuple[models.Usuario | None, models.Empresa | models.Sucursal | None, int | None]:

    get_empresa(db, empresa_id)

    try:
        empresa = (
            db.query(models.Empresa)
            .options(selectinload(models.Empresa.sucursales))
            .filter(models.Empresa.id == empresa_id)
            .with_for_update()
            .first()
        )

        cantidad_sucursales = len([suc for suc in empresa.sucursales if suc.activa])

        if invitacion_rol == 'GERENTE_SUCURSAL' and cantidad_sucursales == 1:
            raise exceptions.EmpresaRolCannotAssignGerenteSucursalError()

        if sucursal_id:
            sucursal = get_sucursal(db, sucursal_id)

            if sucursal.empresa_id != empresa_id:
                raise exceptions.SucursalNotFoundError()

            current_user_rol = verificar_rol_en_empresa_o_sucursal(db, current_user_id, sucursal.empresa_id, sucursal_id)

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
            db.commit()
            return None, None, None

        if not usuario.email_verificado:
            db.commit()
            return None, None, None
        
        # Verificar si ya es miembro de la empresa (rol global)
        es_miembro_en_empresa = db.query(models.Miembro_Empresa.id).filter_by(
            usuario_id=usuario.id,
            empresa_id=empresa_id,
        ).first()

        # Verificar si ya es miembro de alguna sucursal de la empresa
        es_miembro_de_alguna_sucursal = (
            db.query(models.Miembro_Sucursal)
            .join(models.Sucursal)
            .filter(
                models.Miembro_Sucursal.usuario_id == usuario.id,
                models.Sucursal.empresa_id == empresa_id,
            )
            .first()
        )

        if es_miembro_en_empresa or es_miembro_de_alguna_sucursal:
            raise exceptions.EmpresaMiembroAlreadyExistsError()

        db.commit()
    except Exception:
        db.rollback()
        raise

    if sucursal_id:
        return usuario, sucursal, cantidad_sucursales
    else:
        return usuario, empresa, cantidad_sucursales

# Las notificaciones siempre se envian a miembros con roles iguales o inferiores al rol que se desea asignar
# (con excepciones de los empleados que no reciben notificación)
def aceptar_invitacion(db: Session, token: str) -> tuple[str, str, int]:

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        usuario_id = payload.get("usuario_id")
        empresa_id = payload.get("empresa_id")
        sucursal_id = payload.get("sucursal_id")
        rol = payload.get("rol") # nombre del rol (como string, no como entero)
    except JWTError as e:
        raise exceptions.InvitationTokenInvalidExpiredError()
    
    get_empresa(db, empresa_id)
    
    try:
        empresa = (
            db.query(models.Empresa)
            .options(selectinload(models.Empresa.sucursales))
            .filter(models.Empresa.id == empresa_id)
            .with_for_update()
            .first()
        )

        cantidad_sucursales = len([suc for suc in empresa.sucursales if suc.activa])

        if rol == 'GERENTE_SUCURSAL' and cantidad_sucursales == 1:
            raise exceptions.EmpresaRolCannotAssignGerenteSucursalError()
        
        # Buscar usuario por ID
        usuario = db.query(models.Usuario).filter_by(id=usuario_id).first()
        if not usuario:
            raise exceptions.UserNotFoundError()
    
        miembros_de_la_empresa = db.query(models.Miembro_Empresa).options(
            joinedload(models.Miembro_Empresa.rol),
        ).filter(
            models.Miembro_Empresa.empresa_id == empresa_id,
        ).order_by(models.Miembro_Empresa.id.asc()).with_for_update(of=models.Miembro_Empresa).all()
        
        # Verificar si ya es miembro de la empresa (rol global)
        es_miembro_en_empresa = next((m_e for m_e in miembros_de_la_empresa if m_e.usuario_id == usuario_id), None)

        # Verificar si ya es miembro de alguna sucursal de la empresa
        es_miembro_de_alguna_sucursal = (
            db.query(models.Miembro_Sucursal)
            .join(models.Sucursal)
            .filter(
                models.Miembro_Sucursal.usuario_id == usuario.id,
                models.Sucursal.empresa_id == empresa_id,
            )
            .first()
        )

        if es_miembro_en_empresa or es_miembro_de_alguna_sucursal:
            raise exceptions.UserEmpresaMiembroAlreadyExistsError()
        
        if sucursal_id:
            sucursal = get_sucursal(db, sucursal_id)

            if sucursal.empresa_id != empresa_id:
                raise exceptions.SucursalNotFoundError()

            miembros_de_la_sucursal = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.rol),
            ).filter(
                models.Miembro_Sucursal.sucursal_id == sucursal_id,
            ).order_by(models.Miembro_Sucursal.id.asc()).with_for_update(of=models.Miembro_Sucursal).all()

            roles_de_sucursal = ['GERENTE_SUCURSAL', 'EMPLEADO']
            if rol not in roles_de_sucursal:
                raise exceptions.InvitationTokenInvalidExpiredError()
            
            db_rol_id = auxiliares.get_rol_id(db, rol, 'SUCURSAL')
            
            nuevo_miembro = models.Miembro_Sucursal(usuario_id=usuario_id, sucursal_id=sucursal_id, rol_id=db_rol_id)

            extra_data = crear_extra_data_notificacion(
                usuario_id=usuario_id,
                usuario_apellido=usuario.apellido,
                usuario_nombre=usuario.nombre,
                sucursal_id=sucursal.id,
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

            roles_de_empresa = ['PROPIETARIO', 'GERENTE_EMPRESA']
            if rol not in roles_de_empresa:
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
        return auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre), rol, cantidad_sucursales
    else:
        return empresa.nombre, rol, cantidad_sucursales