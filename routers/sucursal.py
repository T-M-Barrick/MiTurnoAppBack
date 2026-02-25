from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, UploadFile, File, Path, Query
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
def create_sucursal(
    nueva_sucursal: schemas_sucursal.SucursalCreate,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursal = crud_sucursal.create(db, current_user.id, nueva_sucursal) # Devuelve un objeto de clase Sucursal de SQLAlchemy
    
    return {}

@router.get("/{sucursal_id}/panel", response_model=schemas_sucursal.SucursalHomeOut, status_code=200)
def acceder_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursal, current_user_rol = crud_sucursal.acceder(db, sucursal_id, current_user.id)
    
    suc = mappers_sucursal.sucursal_home_out(sucursal, current_user_rol)

    return suc

@router.get("/{sucursal_id}/perfil", response_model=schemas_sucursal.SucursalPerfilOut, status_code=200)
def acceder_perfil_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursal, current_user_rol = crud_sucursal.acceder(db, sucursal_id, current_user.id)
    
    suc = mappers_sucursal.sucursal_perfil_out(sucursal, current_user_rol)

    return suc

# Actualizar sucursal (datos simples, teléfonos y dirección)
@router.patch("/{sucursal_id}", response_model=schemas_sucursal.SucursalPerfilOut, status_code=200)
def update_sucursal(
    sucursal_update: schemas_sucursal.SucursalUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursal, current_user_rol = crud_sucursal.update(db, sucursal_id, current_user.id, sucursal_update)

    suc = mappers_sucursal.sucursal_perfil_out(sucursal, current_user_rol)

    return suc

# {"message": "Sucursal desactivada con éxito"}
@router.patch("/{sucursal_id}/desactivar", status_code=204)
def deactivate_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.deactivate(db, sucursal_id, current_user.id)

# {"message": "Sucursal reactivada con éxito"}
@router.patch("/{sucursal_id}/reactivar", status_code=204)
def reactivate_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.reactivate(db, sucursal_id, current_user.id)

# Devuelve todos los clientes de la sucursal según filtros (el primero devuelto será el más reciente en id)
@router.get("/{sucursal_id}/clientes", response_model=schemas_sucursal.ClientesSucursalOut, status_code=200)
def get_clientes_sucursal(
    sucursal_id: int = Path(..., ge=1),
    search: str | None = Query(default=None, min_length=3, max_length=255, alias="busqueda"),
    activo: bool | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    clientes, ultimo_cursor_id = crud_sucursal.get_clientes(
        db, sucursal_id, current_user.id, search=search, activo=activo, id_ultimo=id_ultimo, limit=limit,
    )

    clientes_out = [mappers_sucursal.cliente_out(c) for c in clientes]
    
    respuesta = schemas_sucursal.ClientesSucursalOut(
        clientes=clientes_out, # clientes_out es una lista de objetos de clase ClienteOut de Pydantic
        ultimo_cursor_id=ultimo_cursor_id,
    ) # el campo ultimo_cursor_id volverá si la sucursal pide más clientes
    
    return respuesta

@router.post("/{sucursal_id}/clientes", response_model=schemas_sucursal.ClienteOut, status_code=201)
def create_cliente_sucursal(
    cliente_nuevo: schemas_sucursal.ClienteCreate,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    cliente = crud_sucursal.create_cliente(db, sucursal_id, current_user.id, cliente_nuevo)
    
    cliente_out = mappers_sucursal.cliente_out(cliente)

    return cliente_out

# Actualizar cliente
@router.patch("/{sucursal_id}/clientes/{cliente_id}", response_model=schemas_sucursal.ClienteOut, status_code=200)
def update_cliente_sucursal(
    cliente_update: schemas_sucursal.ClienteUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    cliente = crud_sucursal.update_cliente(db, sucursal_id, current_user.id, cliente_id, cliente_update)

    cliente_out = mappers_sucursal.cliente_out(cliente)

    return cliente_out

@router.patch("/{sucursal_id}/clientes/{cliente_id}/desactivar", status_code=204)
def deactivate_cliente_sucursal(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.deactivate_cliente(db, sucursal_id, current_user.id, cliente_id)

@router.patch("/{sucursal_id}/clientes/{cliente_id}/reactivar", status_code=204)
def reactivate_cliente_sucursal(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.reactivate_cliente(db, sucursal_id, current_user.id, cliente_id)

@router.get("/{sucursal_id}/turnos", response_model=list[schemas_sucursal.TurnoSucursalOut], status_code=200)
def get_turnos_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turnos = crud_sucursal.get_turnos(db, sucursal_id, current_user.id)
    
    turnos_out = [mappers_sucursal.turno_sucursal_out(turno) for turno in turnos]

    return turnos_out

@router.post("/{sucursal_id}/turnos", response_model=schemas_sucursal.TurnoSucursalOut, status_code=201)
def reservar_turno(
    reserva: schemas_sucursal.ReservaTurnoSucursalIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turno = crud_sucursal.reservar_turno(db, sucursal_id, current_user.id, reserva)

    turno_out = mappers_sucursal.turno_sucursal_out(turno)

    return turno_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/{sucursal_id}/turnos/{turno_id}/estado", response_model=schemas_sucursal.TurnoSucursalOut, status_code=200)
def update_estado_turno_sucursal(
    turno_update: schemas_sucursal.TurnoEstadoUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turno_modificado = crud_sucursal.update_estado_turno(db, sucursal_id, current_user, turno_id, turno_update)
    
    turno_out = mappers_sucursal.turno_sucursal_out(turno_modificado)

    return turno_out

@router.delete("/{sucursal_id}/turnos/{turno_id}", status_code=204)
def delete_turno_sucursal(
    sucursal_id: int = Path(..., ge=1),
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.delete_turno(db, sucursal_id, current_user.id, turno_id, constantes.LISTA_PARCIAL_DE_ESTADOS)

@router.get("/{sucursal_id}/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def get_estados_turnos_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turnos = crud_sucursal.get_estados_turnos(db, sucursal_id, current_user.id)

    turnos_estados = [mappers_sucursal.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que la sucursal ya completó (el primero devuelto será el más reciente)
@router.get("/{sucursal_id}/turnos/historial", response_model=schemas_sucursal.HistorialSucursalOut, status_code=200)
def get_historial_sucursal(
    sucursal_id: int = Path(..., ge=1),
    fecha_hora_ultima: datetime | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    # si el fecha_hora_ultima fue pasado, se toma, y si no, se toma datetime.max
    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) if fecha_hora_ultima else datetime.max

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    historial, ultimo_cursor = crud_sucursal.get_historial(
        db, sucursal_id, current_user.id, fecha_hora_ultima=fecha_hora_ultima, id_ultimo=id_ultimo, limit=limit,
    )

    historial_out = [mappers_sucursal.turno_historial_sucursal(h) for h in historial]
    
    respuesta = schemas_sucursal.HistorialSucursalOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialSucursal de Pydantic
        ultimo_cursor_fecha_hora=timezone.ensure_utc(ultimo_cursor[0]) if ultimo_cursor[0] else None,
        ultimo_cursor_id=ultimo_cursor[1],
    ) # los campos ultimo_cursor volverán si la sucursal pide más historial
    
    return respuesta

@router.get("/{sucursal_id}/servicios", response_model=list[schemas_sucursal.ServicioSucursalOut], status_code=200)
def get_servicios_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    servicios = crud_sucursal.get_servicios(db, sucursal_id, current_user.id)
    
    servicios_out = [mappers_sucursal.servicio_sucursal_out(servicio) for servicio in servicios]

    return servicios_out

@router.post("/{sucursal_id}/servicios", response_model=schemas_sucursal.ServicioSucursalOut, status_code=201)
def create_servicio_sucursal(
    servicio_nuevo: schemas_sucursal.ServicioCreate,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    servicio = crud_sucursal.create_servicio(db, sucursal_id, current_user.id, servicio_nuevo)
    
    servicio_out = mappers_sucursal.servicio_sucursal_out(servicio)

    return servicio_out

@router.patch("/{sucursal_id}/servicios/{servicio_id}", response_model=schemas_sucursal.ServicioSucursalOut, status_code=200)
def update_servicio_sucursal(
    servicio_update: schemas_sucursal.ServicioUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    servicio_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    servicio = crud_sucursal.update_servicio(db, sucursal_id, servicio_id, current_user.id, servicio_update)
    
    servicio_out = mappers_sucursal.servicio_sucursal_out(servicio)

    return servicio_out

# if len(servicios_delete.servicios) == 1:
#     return {"message": "Servicio eliminado con éxito"}
# else:
#     return {"message": "Servicios eliminados con éxito"}
@router.delete("/{sucursal_id}/servicios", status_code=204)
def delete_servicios_sucursal(
    servicios_delete: schemas_sucursal.ServiciosDeleteIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.delete_servicios(db, sucursal_id, current_user.id, servicios_delete.servicios)

@router.get("/{sucursal_id}/miembros", response_model=list[schemas_sucursal.MiembroSucursalOut], status_code=200)
def get_miembros_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    miembros = crud_sucursal.get_miembros(db, sucursal_id, current_user.id)
    
    miembros_out = [mappers_sucursal.miembro_sucursal_out(miembro) for miembro in miembros]

    return miembros_out

@router.delete("/{sucursal_id}/miembros/me", status_code=204)
def leave_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.leave_sucursal(db, sucursal_id, current_user.id)

# "message": f"Rol de {apellido}, {nombre} añadido a la sucursal con éxito"
# endpoint para agregar a un miembro ya de una sucursal de una empresa a otra sucursal de la misma empresa sin borrarlo de ninguna otra sucursal
@router.post("/{sucursal_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembrosEmpresaOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def add_miembro_sucursal(
    data: schemas_sucursal.MiembroSucursalAddIn,
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    # miembro es una lista de objetos Miembro_Sucursal
    miembro = crud_sucursal.add_miembro(db, sucursal_id, current_user.id, target_id, data.nuevo_rol)

    miembro_out = mappers_empresa.miembros_empresa_out([], miembro)

    return miembro_out

# "message": f"Rol de {apellido}, {nombre} modificado a {nuevo_rol}"
@router.patch("/{sucursal_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembrosEmpresaOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def update_rol(
    data: schemas_common.UpdateRolIn,
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    miembro = crud_sucursal.update_rol(db, sucursal_id, current_user.id, target_id, data.nuevo_rol)

    if isinstance(miembro, models.Miembro_Empresa):
        miembro_out = mappers_empresa.miembros_empresa_out([miembro], [])
    if isinstance(miembro, list[models.Miembro_Sucursal]):
        miembro_out = mappers_empresa.miembros_empresa_out([], miembro)

    return miembro_out

# {"message": f"{apellido}, {nombre} fue eliminado correctamente de esta sucursal"}
@router.delete("/{sucursal_id}/miembros/{target_id}", status_code=204) # target_id es el id del miembro como usuario en la tabla usuario
def delete_miembro_sucursal(
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.delete_miembro(db, sucursal_id, current_user.id, target_id)

@router.get("/{sucursal_id}/bloqueos", response_model=list[schemas_sucursal.BlockClienteOut], status_code=200)
def get_clientes_bloqueados_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    resultados = crud_sucursal.get_clientes_bloqueados(db, sucursal_id, current_user.id)
    
    bloqueos_out = [mappers_sucursal.block_cliente_out(bloqueo, miembro_rol) for bloqueo, miembro_rol in resultados]

    return bloqueos_out

@router.post("/{sucursal_id}/bloqueos/{cliente_id}", response_model=schemas_sucursal.BlockClienteOut, status_code=201)
def block_cliente_sucursal(
    data: schemas_sucursal.BlockClienteIn,
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    bloqueo, miembro_rol = crud_sucursal.block_cliente(db, sucursal_id, current_user.id, cliente_id, data.motivo)

    bloqueo_out =  mappers_sucursal.block_cliente_out(bloqueo, miembro_rol)

    return bloqueo_out

@router.delete("/{sucursal_id}/bloqueos/{cliente_id}", status_code=204)
def unlock_cliente_sucursal(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_sucursal.unlock_cliente(db, sucursal_id, current_user.id, cliente_id)