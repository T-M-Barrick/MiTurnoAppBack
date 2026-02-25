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

    empresa_existe = db.query(models.Empresa).filter_by(email=empresa.email).first()
    if empresa_existe and empresa_existe.email_verificado:
        raise exceptions.EmpresaAlreadyExistsError()
    if empresa_existe and not empresa_existe.email_verificado:
        raise empresa_existe
    
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
            empresa_id=db_empresa.id
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

    rol = db.query(models.Rol).filter_by(nombre="PROPIETARIO").first()

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())
    
    db_miembro = models.Miembro(usuario_id=usuario_id, empresa_id=empresa_id, rol_id=rol.id, created_at=ahora_utc)
    db.add(db_miembro)

def acceder(db: Session, empresa_id: int, usuario_id: int):

    empresa = get_empresa(db, empresa_id)
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)

    return empresa, current_user_rol

def update(db: Session, empresa_id: int, usuario_id: int, empresa_update: schemas_empresa.EmpresaUpdateIn):

    db_emp = get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    
    try:
        for attr, value in empresa_update.dict(exclude_unset=True).items():
            setattr(db_emp, attr, value)

        db.commit()
    except Exception:
        db.rollback()
        raise

    empresa = db.query(models.Empresa).filter_by(id=empresa_id).first()

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
    ).filter(
        models.Miembro_Empresa.empresa_id == empresa_id,
    ).all()
    
    miembros_sucursales = db.query(models.Miembro_Sucursal).join(models.Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.sucursal),
    ).filter(
        models.Sucursal.empresa_id == empresa_id,
    ).all()

    return miembros_empresa, miembros_sucursales

def get_miembro_empresa(db: Session, empresa_id: int, usuario_miembro_id: int):

    miembro_empresa = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario)).filter_by(
            usuario_id=usuario_miembro_id, empresa_id=empresa_id).first()
    
    if not miembro_empresa:
        raise exceptions.EmpresaMiembroNotFoundError()

    return miembro_empresa

def contar_propietarios(db: Session, empresa_id: int):

    cant = db.query(models.Miembro_Empresa).filter(
        models.Miembro_Empresa.empresa_id == empresa_id,
        models.Miembro_Empresa.rol == 1).count()

    return cant

# Esta función es solo para que un propietario pueda modificar un rol de gerente de empresa a otro
# o para que un propietario se degrade a gerente de empresa a sí mismo
def update_rol(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str, sucursal_id: str | None):

    get_empresa(db, empresa_id)

    if sucursal_id:
        get_sucursal(db, sucursal_id)

    miembro_empresa_target = get_miembro_empresa(db, empresa_id, target_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    if current_user_rol != 'propietario':
        raise exceptions.EmpresaRolUpdateError()
    
    roles_sucursales = ['gerente_sucursal', 'empleado']

    miembro_empresa_target_rol_actual = auxiliares.transformar_rol(miembro_empresa_target.rol, contexto="empresa") # string

    if usuario_solicitante_id == target_id: # se modifica él mismo

        if nuevo_rol == 'propietario':
            return miembro_empresa_target # no tiene sentido modificarlo ya que es el mismo propietario cambiándose a propietario
        
        propietarios = contar_propietarios(db, empresa_id)
        if propietarios <= 1 and nuevo_rol != 'propietario':
            raise exceptions.EmpresaPropietarioOutError()

        if nuevo_rol in roles_sucursales:
            raise exceptions.EmpresaPersonalRolPropietarioUpdateError()
        
        # Si se llegó hasta este punto del flujo, significa que el propietario se degrada a gerente de empresa

    else: # modifica a otro miembro

        if not auxiliares.rol_superior(current_user_rol, miembro_empresa_target_rol_actual):
            raise exceptions.EmpresaRolUpdateError()
        
        if miembro_empresa_target_rol_actual == 'gerente_empresa' and nuevo_rol == 'gerente_empresa':
            return miembro_empresa_target # no tiene sentido modificarlo ya que es un gerente de empresa pasando a ser gerente de empresa
            
        # Si se llegó hasta este punto del flujo, significa que un propietario modifica a un gerente de empresa a cualquier otro rol
    
    try:
        if nuevo_rol in roles_sucursales: # signifca que un gerente de empresa pasa a ser gerente de sucursal o empleado

            db_nuevo_rol = auxiliares.transformar_rol(nuevo_rol, contexto="sucursal") # int

            miembro = models.Miembro_Sucursal(
                usuario_id=target_id,
                sucursal_id=sucursal_id,
                rol=db_nuevo_rol,
            )
            db.add(miembro)
            db.delete(miembro_empresa_target)
            db.commit()

            miembro_sucursales = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.usuario),
                joinedload(models.Miembro_Sucursal.sucursal)).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

            return miembro_sucursales

        else: # signifca que un gerente de empresa pasa a ser propietario

            db_nuevo_rol = auxiliares.transformar_rol(nuevo_rol, contexto="empresa") # int

            miembro_empresa_target.rol = db_nuevo_rol
            db.commit()
            db.refresh(miembro_empresa_target)

            return miembro_empresa_target

    except Exception:
        db.rollback()
        raise

# El usuario de la empresa se borra de esta
def leave_empresa(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    # Traer el objeto de clase Miembro_Empresa que se eliminará
    miembro_empresa = get_miembro_empresa(db, empresa_id, usuario_id)

    miembro_empresa_rol = auxiliares.transformar_rol(miembro_empresa.rol, contexto="empresa") # string

    if miembro_empresa_rol == "propietario":
        propietarios = contar_propietarios(db, empresa_id)
        if propietarios <= 1:
            raise exceptions.EmpresaPropietarioOutError()

    servicios = db.query(models.Servicio).join(models.Sucursal).filter(
        models.Sucursal.empresa_id == empresa_id,
        models.Servicio.profesional_id == usuario_id).all()

    try:
        for servicio in servicios:

            turno_confirmado = db.query(models.Turno).filter(
                models.Turno.servicio_id == servicio.id,
                models.Turno.estado_turno_sucursal_id == 1,
            ).first()

            if turno_confirmado:
                raise exceptions.EmpresaProfesionalConTurnosConfimadosOutError()

            db.delete(servicio)
        
        db.delete(miembro_empresa)
        db.commit()
    except Exception:
        db.rollback()
        raise

def delete_miembro(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    if usuario_solicitante_id == target_id:
        raise exceptions.EmpresaInvalidSelfRemovalError()

    # Traer el objeto de clase Miembro_Empresa que se eliminará
    miembro_empresa_target = get_miembro_empresa(db, empresa_id, target_id)

    miembro_empresa_target_rol = auxiliares.transformar_rol(miembro_empresa_target.rol, contexto="empresa") # string

    if not auxiliares.rol_superior(current_user_rol, miembro_empresa_target_rol):
        raise exceptions.EmpresaMiembroDeleteError()
    
    servicios = db.query(models.Servicio).join(models.Sucursal).filter(
        models.Sucursal.empresa_id == empresa_id,
        models.Servicio.profesional_id == target_id).all()
    
    try:
        for servicio in servicios:

            turno_confirmado = db.query(models.Turno).filter(
                models.Turno.servicio_id == servicio.id,
                models.Turno.estado_turno_sucursal_id == 1,
            ).first()

            if turno_confirmado:
                raise exceptions.EmpresaMiembroDeleteConTurnosConfirmadosError()

            db.delete(servicio)

        db.delete(miembro_empresa_target)

        db.commit()

    except Exception:
        db.rollback()
        raise