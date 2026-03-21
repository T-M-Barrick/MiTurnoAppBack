from datetime import datetime, timedelta

from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload
import cloudinary.uploader

from crud.common import get_empresa, get_sucursal, verificar_rol_en_empresa, nuevo_estado_check
from core import models, constantes, exceptions, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa

# Crear empresa
def create(db: Session, usuario_id: int, empresa: schemas_empresa.EmpresaCreate):

    email_normalizado = models.normalizar_email(empresa.email)

    empresa_existe = db.query(models.Empresa).filter_by(email_normalizado=email_normalizado).first()
    if empresa_existe and empresa_existe.email_verificado:
        raise exceptions.EmpresaAlreadyExistsError()
    if empresa_existe and not empresa_existe.email_verificado:
        return empresa_existe
    
    try:
        # Crear el objeto de empresa
        db_empresa = models.Empresa(
            cuit=empresa.cuit,
            nombre=empresa.nombre,
            email=empresa.email,
            email_verificado=False,
            rubro=empresa.rubro,
            rubro2=empresa.rubro2,
            logo_url=None,
            logo_public_id=None,
            fecha_hora_alta=None,
        )

        db.add(db_empresa)
        db.flush()

        # Crear el objeto de sucursal
        db_sucursal = models.Sucursal(
            empresa_id=db_empresa.id,
            cuit=empresa.cuit,
            nombre=None,
            email=None,
            email_verificado=None,
            reserva_publica_habilitada=empresa.reserva_publica_habilitada,
            activa=False,
        )

        db.add(db_sucursal)
        db.flush()

        # Agregar teléfonos
        for t in empresa.telefonos:
            db_tel = models.Telefono(numero=t.numero, sucursal_id=db_sucursal.id)
            db.add(db_tel)

        # Agregar dirección
        db_dir = models.Direccion(
            sucursal_id=db_sucursal.id,
            calle=empresa.direccion.calle,
            altura=empresa.direccion.altura,
            localidad=empresa.direccion.localidad,
            departamento=empresa.direccion.departamento,
            provincia=empresa.direccion.provincia,
            pais=empresa.direccion.pais,
            lat=empresa.direccion.lat,
            lng=empresa.direccion.lng,
            aclaracion=empresa.direccion.aclaracion)

        db.add(db_dir)

        asignar_rol_de_propietario(db, usuario_id, db_empresa.id)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return db_empresa

def asignar_rol_de_propietario(db: Session, usuario_id: int, empresa_id: int):
    
    db_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol_id=1)
    db.add(db_miembro)

def acceder(db: Session, empresa_id: int, usuario_id: int):

    empresa = get_empresa(db, empresa_id)
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)

    return empresa, current_user_rol

def update(db: Session, empresa_id: int, usuario_id: int, empresa_update: schemas_empresa.EmpresaUpdateIn):

    empresa = get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    
    try:
        for attr, value in empresa_update.model_dump(exclude_unset=True).items():
            setattr(empresa, attr, value)
        
        for sucursal in empresa.sucursales:
            # Para disparar el evento definido en models y que se actualice busqueda_texto de sucursal (el None nunca se inserta)
            sucursal.busqueda_texto = None

        db.commit()
        db.refresh(empresa)
    except Exception:
        db.rollback()
        raise

    return empresa, current_user_rol

def update_logo(db: Session, empresa_id: int, file: UploadFile | None):

    empresa = get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)
    
    # Si no mandan archivo, borrar
    if file is None:
        if empresa.logo_public_id:
            cloudinary.uploader.destroy(empresa.logo_public_id)

        logo_url = None
        logo_public_id = None

    else:
        if not file.content_type.startswith("image/"):
            raise exceptions.LogoInvalidError(field="logo")

        content = file.file.read()
        
        auxiliares.validar_logo(content) # valido el logo

        # Creo el Public ID fijo por empresa
        public_id = f"empresa_{empresa.id}_logo"

        # Subir (overwrite)
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            overwrite=True,
            resource_type="image"
        )

        logo_url = result["secure_url"]
        logo_public_id = result["public_id"]

    try:
        empresa.logo_url = logo_url
        empresa.logo_public_id = logo_public_id
        db.commit()
        db.refresh(empresa)
    except Exception:
        db.rollback()
        raise
    
    return empresa.logo_url

def get_sucursales_desactivadas(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    sucursales = (
        db.query(models.Sucursal)
        .options(
            selectinload(models.Sucursal.telefonos),
            joinedload(models.Sucursal.direccion),
        )
        .filter(
            models.Sucursal.empresa_id == empresa_id,
            models.Sucursal.activa == False,
        )
        .all()
    )

    return sucursales

def get_miembros(db: Session, empresa_id: int, usuario_solicitante_id: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    miembros_empresa = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario),
        joinedload(models.Miembro_Empresa.rol),
    ).filter(
        models.Miembro_Empresa.empresa_id == empresa_id,
    ).all()
    
    miembros_sucursales = db.query(models.Miembro_Sucursal).join(models.Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.sucursal),
        joinedload(models.Miembro_Sucursal.rol),
    ).filter(
        models.Sucursal.empresa_id == empresa_id,
    ).all()

    return miembros_empresa, miembros_sucursales

def get_miembro_empresa(db: Session, empresa_id: int, usuario_miembro_id: int, lanzar_error: bool = True, bloquear: bool = False):

    query = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario),
        joinedload(models.Miembro_Empresa.rol),
    ).filter_by(
        usuario_id=usuario_miembro_id,
        empresa_id=empresa_id,
    )

    if bloquear:
        query = query.with_for_update(of=models.Miembro_Empresa)

    miembro_empresa = query.first()
    
    if not miembro_empresa and lanzar_error:
        raise exceptions.EmpresaMiembroNotFoundError()

    return miembro_empresa

def contar_propietarios(db: Session, empresa_id: int):

    cant = db.query(models.Miembro_Empresa).filter(
        models.Miembro_Empresa.empresa_id == empresa_id,
        models.Miembro_Empresa.rol_id == 1,
    ).count()

    return cant

# El usuario de la empresa se borra de esta
def leave_empresa(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)

    try:
        empresa = (
            db.query(models.Empresa)
            .filter(models.Empresa.id == empresa_id)
            .with_for_update()
            .first()
        )

        verificar_rol_en_empresa(db, usuario_id, empresa_id)

        # Traer el objeto de clase Miembro_Empresa que se eliminará
        miembro_empresa = get_miembro_empresa(db, empresa_id, usuario_id, bloquear=True)

        miembro_empresa_rol = miembro_empresa.rol.nombre

        if miembro_empresa_rol == "PROPIETARIO":
            propietarios = contar_propietarios(db, empresa_id)
            if propietarios <= 1:
                raise exceptions.EmpresaPropietarioOutError()

        servicios_base = db.query(models.ServicioBase).join(models.Sucursal).filter(
            models.Sucursal.empresa_id == empresa_id,
            models.ServicioBase.profesional_id == usuario_id,
        ).order_by(models.ServicioBase.id.asc()).with_for_update(of=models.ServicioBase).all()

        ids_servicios_base = [s.id for s in servicios_base]

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(ids_servicios_base),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        turno_confirmado = (
            db.query(models.Turno.id)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.EmpresaProfesionalConTurnosConfimadosOutError()
        
        for servicio_base in servicios_base:
            db.delete(servicio_base) # CASCADE borra servicios versionados (con sus disponibilidades) y excepciones
        
        db.delete(miembro_empresa)
        db.commit()
    except Exception:
        db.rollback()
        raise

# Esta función es solo para que un propietario pueda modificar un rol de gerente de empresa a otro
# o para que un propietario se degrade a gerente de empresa a sí mismo
def update_rol(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str, sucursal_id: int | None):

    get_empresa(db, empresa_id)

    try:
        empresa = (
            db.query(models.Empresa)
            .filter(models.Empresa.id == empresa_id)
            .with_for_update()
            .first()
        )

        if sucursal_id:
            get_sucursal(db, sucursal_id)
        
        current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

        if current_user_rol != 'PROPIETARIO':
            raise exceptions.EmpresaRolUpdateError()

        miembro_empresa_target = get_miembro_empresa(db, empresa_id, target_id, bloquear=True)

        miembro_empresa_target_rol_actual = miembro_empresa_target.rol.nombre
        
        roles_sucursales = ['GERENTE_SUCURSAL', 'EMPLEADO']

        if usuario_solicitante_id == target_id: # se modifica él mismo

            if nuevo_rol == 'PROPIETARIO':
                db.commit() # para desbloquear lo que bloqueamos con with_for_update()
                return miembro_empresa_target # no tiene sentido modificarlo ya que es el mismo propietario cambiándose a propietario
            
            propietarios = contar_propietarios(db, empresa_id)
            if propietarios <= 1 and nuevo_rol != 'PROPIETARIO':
                raise exceptions.EmpresaPropietarioOutError()

            if nuevo_rol in roles_sucursales:
                raise exceptions.EmpresaPersonalRolPropietarioUpdateError()
            
            # Si se llegó hasta este punto del flujo, significa que el propietario se degrada a gerente de empresa

        else: # modifica a otro miembro

            if not auxiliares.rol_superior(current_user_rol, miembro_empresa_target_rol_actual):
                raise exceptions.EmpresaRolUpdateError()
            
            if miembro_empresa_target_rol_actual == 'GERENTE_EMPRESA' and nuevo_rol == 'GERENTE_EMPRESA':
                db.commit() # para desbloquear lo que bloqueamos con with_for_update()
                return miembro_empresa_target # no tiene sentido modificarlo ya que es un gerente de empresa pasando a ser gerente de empresa
                
            # Si se llegó hasta este punto del flujo, significa que un propietario modifica a un gerente de empresa a cualquier otro rol
    
        if nuevo_rol in roles_sucursales: # signifca que un gerente de empresa pasa a ser gerente de sucursal o empleado

            db_nuevo_rol_id = auxiliares.get_rol_id(db, nuevo_rol, 'SUCURSAL')

            miembro = models.Miembro_Sucursal(
                usuario_id=target_id,
                sucursal_id=sucursal_id,
                rol_id=db_nuevo_rol_id,
            )
            db.add(miembro)
            db.delete(miembro_empresa_target)
            db.commit()

            miembro_sucursales = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.usuario),
                joinedload(models.Miembro_Sucursal.sucursal),
                joinedload(models.Miembro_Sucursal.rol),
            ).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

            return miembro_sucursales

        else: # signifca que un gerente de empresa pasa a ser propietario

            db_nuevo_rol_id = auxiliares.get_rol_id(db, nuevo_rol, 'EMPRESA')

            miembro_empresa_target.rol_id = db_nuevo_rol_id
            db.commit()
            
            miembro_empresa_target = get_miembro_empresa(db, empresa_id, target_id)

            return miembro_empresa_target

    except Exception:
        db.rollback()
        raise

def delete_miembro(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    if usuario_solicitante_id == target_id:
        raise exceptions.EmpresaInvalidSelfRemovalError()
    
    try:
        # Traer el objeto de clase Miembro_Empresa que se eliminará
        miembro_empresa_target = get_miembro_empresa(db, empresa_id, target_id, bloquear=True)

        miembro_empresa_target_rol = miembro_empresa_target.rol.nombre

        if not auxiliares.rol_superior(current_user_rol, miembro_empresa_target_rol):
            raise exceptions.EmpresaMiembroDeleteError()
    
        servicios_base = db.query(models.ServicioBase).join(models.Sucursal).filter(
            models.Sucursal.empresa_id == empresa_id,
            models.ServicioBase.profesional_id == target_id,
        ).order_by(models.ServicioBase.id.asc()).with_for_update(of=models.ServicioBase).all()

        ids_servicios_base = [s.id for s in servicios_base]

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(ids_servicios_base),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        turno_confirmado = (
            db.query(models.Turno.id)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.EmpresaMiembroDeleteWithTurnosConfirmadosError()
        
        for servicio_base in servicios_base:
            db.delete(servicio_base) # CASCADE borra servicios versionados (con sus disponibilidades) y excepciones

        db.delete(miembro_empresa_target)
        db.commit()
    except Exception:
        db.rollback()
        raise

'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /empresas/5/notificaciones?leidas=false&id_ultimo=1234&limit=20
'''
def get_notificaciones(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    leidas: bool | None = None,
    id_ultimo: int | None = None,
    limit: int = 20,
):
    '''
    Devuelve las notificaciones de una empresa con paginación.
    Van ordenadas de la más reciente a la más antigua (fecha descendente).

    Parámetros:
        leidas: si es None, devuelve tanto las leidas como las no leidas.
        id_ultimo: id de la última notificación recibida (para la siguiente página).
        limit: cantidad máxima de notificaciones a devolver (máx 100).
    
    Proceso:
        Primera solicitud (en login): front no envía cursor → back devuelve primeros N registros + cursor del último.
        Siguientes solicitudes: front envía cursor → back devuelve los siguientes N registros + cursor actualizado.
        Última página: back devuelve lista vacía y cursor None → front deja de pedir más.
    '''
    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    query = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.empresa_id == empresa_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
    )

    # Aplicar paginación por cursor si se envió id_ultimo
    if id_ultimo:
        query = query.filter(
            models.Notificacion.id < id_ultimo,
        )
    
    # Filtro por leidas (IMPORTANTE usar is not None)
    if leidas is not None:
        query = query.filter(
            models.Notificacion.leida == leidas,
        )

    query = query.order_by(models.Notificacion.id.desc())

    limit = min(limit, 100) # no más de 100 por consulta

    # notificaciones es una lista de objetos de clase Notificacion de SQLAlchemy
    notificaciones = query.limit(limit).all()

    ultimo_cursor_id = notificaciones[-1].id if notificaciones else None

    return notificaciones, ultimo_cursor_id

def get_notificaciones_nuevas(db: Session, empresa_id: int, usuario_id: int, id_posterior: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    notificaciones_nuevas = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.empresa_id == empresa_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
        models.Notificacion.id > id_posterior,
    ).order_by(models.Notificacion.id.desc()).all()

    return notificaciones_nuevas

def update_notificacion_leida(db: Session, empresa_id: int, usuario_id: int, notificacion_id: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    try:
        filas = db.query(models.Notificacion).filter(
            models.Notificacion.id == notificacion_id,
            models.Notificacion.usuario_id == usuario_id, # chequeo que el mismo usuario de la notificación sea el que hace la request
            models.Notificacion.empresa_id == empresa_id, # chequeo adicional de la empresa
        ).update(
            {"leida": True},
            synchronize_session=False
        )

        if filas == 0:
            raise exceptions.NotificationNotFoundError()

        db.commit()
    except Exception:
        db.rollback()
        raise