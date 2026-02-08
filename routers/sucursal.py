from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, exceptions, config, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import sucursal as crud_sucursal
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal
from mappers import sucursal as mappers_sucursal

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])

# {"message": "Sucursal creada con éxito"}
@router.post("/", status_code=201)
def create_sucursal(sucursal_nueva: schemas_sucursal.SucursalCreate, response: Response, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    try:
        sucursal = crud_sucursal.create_sucursal(db, sucursal_nueva) # Devuelve un objeto de clase Sucursal de SQLAlchemy

        if empresa and empresa.email_verificado:
            return {}

        crud_empresa.asignar_rol_de_propietario(db=db, usuario_id=current_user.id, empresa_id=empresa.id)

        # Enviar el mail
        limite_no_sobrepasado = crud_common.check_email_rate_limit(db, empresa.email, "REGISTER")

        if limite_no_sobrepasado:

            token = autenticacion.create_email_token(
                data={"sub": empresa.id},
                expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS)
            )

            try:
                mensajes.send_verification_email(usuario.email, token)
            except exceptions.EmailSendFailedError:
                pass # no revelamos si el email se mandó o no

        db.commit()

    except Exception:
        db.rollback()
        raise
    
    return {}

# {"message": "Correo verificado con éxito"}
@router.get("/verificacion/email", status_code=204)
def verificacion_email_sucursal(token: str, db: Session = Depends(get_db)):

    crud_common.verificacion_email(db, token, usuario=False)

@router.get("/{sucursal_id}", response_model=schemas_sucursal.SucursalHomeOut, status_code=200)
def acceder_sucursal(sucursal_id: int, current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    sucursal, current_user_rol = crud_sucursal.acceder(db, sucursal_id, current_user.id)
    
    emp = mappers_sucursal.sucursal_home_out(sucursal, current_user_rol)

    return emp

# Actualizar sucursal (datos simples, teléfonos y dirección)
@router.patch("/{sucursal_id}", response_model=schemas_sucursal.SucursalHomeOut, status_code=200)
def update_sucursal(sucursal_id: int, sucursal_update: schemas_sucursal.SucursalUpdateIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    sucursal, current_user_rol = crud_sucursal.update(db, sucursal_id, current_user.id, sucursal_update)

    emp = mappers_sucursal.sucursal_home_out(sucursal, current_user_rol)

    return emp

@router.patch("/empresas/{empresa_id}/logo", response_model=schemas_empresa.EmpresaLogoOut, status_code=200)
def update_empresa_logo(
    empresa_id: int,
    file: UploadFile | None = File(None),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    logo_url = crud.update_logo(db, empresa_id, file)

    logo_out = mappers_empresa.empresa_logo_out(logo_url)

    return logo_out

@router.get("/{empresa_id}/turnos", response_model=list[schemas_empresa.TurnoEmpresaOut], status_code=200)
def get_turnos_empresa(
    empresa_id: int,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    turnos = crud_empresa.get_turnos(db, empresa_id, current_user.id)
    
    turnos_out = [mappers_empresa.turno_empresa_out(turno) for turno in turnos]

    return turnos_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/{empresa_id}/turnos", response_model=schemas_empresa.TurnoEmpresaOut, status_code=200)
def update_turno_empresa(
    empresa_id: int,
    turno_update: schemas_common.TurnoUpdateIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    turno_modificado = crud_empresa.update_turno(db, empresa_id, current_user, turno_update)
    
    turno_out = mappers_empresa.turno_empresa_out(turno_modificado)

    return turno_out

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
@router.delete("/{empresa_id}/turnos/{turno_id}", status_code=204)
def delete_turno_empresa(empresa_id: int, turno_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_empresa.delete_turno(db, empresa_id, current_user.id, turno_id, constantes.LISTA_PARCIAL_DE_ESTADOS)

@router.get("/{empresa_id}/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def get_estados_turnos_empresa(empresa_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    turnos = crud_empresa.get_estados_turnos(db, empresa_id, current_user.id)

    turnos_estados = [mappers_empresa.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que la empresa ya completó (tabla Historial) (el primero devuelto será el más reciente)
@router.get("/{empresa_id}/historial", response_model=schemas_empresa.HistorialEmpresaOut, status_code=200)
def get_historial_empresa(empresa_id: int, current_user: models.Usuario = Depends(autenticacion.get_current_user), 
    db: Session = Depends(get_db), before: Optional[datetime] = Query(None)):
    
    fecha_hora_ultima = timezone.to_naive_utc(before) if before else datetime.max # si el before fue pasado, se toma, y si no, se toma datetime.max

    historial, ultimo_cursor = crud_empresa.get_historial(
        db, empresa_id, current_user.id, fecha_hora_ultima=fecha_hora_ultima)

    historial_out = [mappers_empresa.turno_historial_empresa(h) for h in historial]
    
    respuesta = schemas_empresa.HistorialEmpresaOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialEmpresa de Pydantic
        ultimo_cursor=timezone.ensure_utc(ultimo_cursor)) # ultimo_cursor volverá si el usuario pide más historial
    
    return respuesta

@router.get("/{empresa_id}/servicios", response_model=list[schemas_empresa.ServicioEmpresaOut], status_code=200)
def get_servicios_empresa(
    empresa_id: int,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    servicios = crud_empresa.get_servicios(db, empresa_id, current_user.id)
    
    servicios_out = [mappers_empresa.servicio_empresa_out(servicio) for servicio in servicios]

    return servicios_out

@router.post("/{empresa_id}/servicios", response_model=schemas_empresa.ServicioEmpresaOut, status_code=201)
def create_servicio_empresa(
    empresa_id: int,
    servicio_nuevo: schemas_empresa.ServicioCreate,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    servicio = crud_empresa.create_servicio(db, empresa_id, current_user.id, servicio_nuevo)
    
    servicio_out = mappers_empresa.servicio_empresa_out(servicio)

    return servicio_out

@router.patch("/{empresa_id}/servicios", response_model=schemas_empresa.ServicioEmpresaOut, status_code=200)
def update_servicio_empresa(
    empresa_id: int,
    servicio_update: schemas_empresa.ServicioUpdateIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    servicio = crud_empresa.update_servicio(db, empresa_id, current_user.id, servicio_update)
    
    servicio_out = mappers_empresa.servicio_empresa_out(servicio)

    return servicio_out

# if len(servicios_delete.servicios) == 1:
#     return {"message": "Servicio eliminado con éxito"}
# else:
#     return {"message": "Servicios eliminados con éxito"}
@router.delete("/{empresa_id}/servicios", status_code=204)
def delete_servicios_empresa(
    empresa_id: int,
    servicios_delete: schemas_empresa.ServiciosDeleteIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    crud_empresa.delete_servicios(db, empresa_id, current_user.id, servicios_delete.servicios)

@router.get("/{empresa_id}/miembros", response_model=list[schemas_empresa.MiembroOut], status_code=200)
def get_miembros_empresa(
    empresa_id: int,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    miembros = crud_empresa.get_miembros(db, empresa_id, current_user.id)
    
    miembros_out = [mappers_empresa.miembro_out(miembro) for miembro in miembros]

    return miembros_out

@router.patch("/{empresa_id}/miembros/me", response_model=schemas_empresa.RolOut, status_code=200)
def update_personal_rol(empresa_id: int, data: schemas_empresa.UpdateRolIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    rol_nombre = crud_empresa.update_rol(db, empresa_id, current_user.id, current_user.id, data.nuevo_rol)

    rol_out = mappers_empresa.rol_out(rol_nombre)

    return rol_out

@router.delete("/{empresa_id}/miembros/me", status_code=204)
def empresa_out(empresa_id: int, current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_empresa.empresa_out(db, empresa_id, current_user.id)

# return "message": f"Rol de {miembro_empresa.usuario.apellido}, {miembro_empresa.usuario.nombre} modificado a {nuevo_rol}"
@router.patch("/{empresa_id}/miembros/{target_id}",
    response_model=schemas_empresa.RolOut, status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def update_rol(empresa_id: int, target_id: int, data: schemas_empresa.UpdateRolIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    rol_nombre = crud_empresa.update_rol(db, empresa_id, current_user.id, target_id, data.nuevo_rol)

    rol_out = mappers_empresa.rol_out(rol_nombre)

    return rol_out

# {"message": f"{apellido}, {nombre} fue eliminado correctamente de esta empresa"}
@router.delete("/{empresa_id}/miembros/{target_id}", status_code=204) # target_id es el id del miembro como usuario en la tabla usuario
def delete_miembro(empresa_id: int, target_id: int,
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_empresa.delete_miembro(db, empresa_id, current_user.id, target_id)

@router.get("/{empresa_id}/bloqueos", response_model=list[schemas_empresa.BlockUserOut], status_code=200)
def get_usuarios_bloqueados(
    empresa_id: int,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db)):

    resultados = crud_empresa.get_usuarios_bloqueados(db, empresa_id, current_user.id)
    
    bloqueos_out = [mappers_empresa.block_user_out(bloqueo, miembro_rol) for bloqueo, miembro_rol in resultados]

    return bloqueos_out

@router.post("/{empresa_id}/bloqueos",
    response_model=schemas_empresa.BlockUserOut, status_code=201)
def block_usuario(empresa_id: int, data: schemas_empresa.BlockUserIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    bloqueo, miembro_rol = crud_empresa.block_usuario(db, empresa_id, current_user.id, data.email, data.motivo)

    bloqueo_out =  mappers_empresa.block_user_out(bloqueo, miembro_rol)

    return bloqueo_out

@router.delete("/{empresa_id}/bloqueos", status_code=204)
def unlock_usuario(empresa_id: int, data: schemas_empresa.UnlockUserIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_empresa.unlock_usuario(db, empresa_id, current_user.id, data.email)