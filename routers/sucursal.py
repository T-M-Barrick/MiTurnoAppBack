from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from fastapi.exceptions import RequestValidationError
from pydantic import EmailStr
from sqlalchemy.orm import Session # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import sucursal as crud_sucursal
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal
from schemas import empresa as schemas_empresa
from mappers import common as mappers_common
from mappers import sucursal as mappers_sucursal
from mappers import empresa as mappers_empresa

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])

@router.post("/", response_model=schemas_empresa.SucursalPerfilOut, status_code=201)
def crear_sucursal(
    nueva_sucursal: schemas_sucursal.SucursalCreate,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.SucursalPerfilOut:

    sucursal = crud_sucursal.crear(db, current_user.id, nueva_sucursal)

    sucursal_out = mappers_empresa.sucursal_perfil_out(sucursal)
    
    return sucursal_out

@router.get("/{sucursal_id}/panel", response_model=schemas_sucursal.SucursalHomeOut, status_code=200)
def acceder_panel(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.SucursalHomeOut:

    sucursal, current_user_rol = crud_sucursal.acceder(db, sucursal_id, current_user.id)

    notificaciones, ultimo_cursor_id = crud_common.obtener_notificaciones(db, current_user.id, sucursal_id=sucursal_id)

    cantidad_sucursales_activas = crud_sucursal.cant_sucursales_activas(db, sucursal.empresa_id)

    suc = mappers_sucursal.sucursal_home_out(sucursal, notificaciones, ultimo_cursor_id, current_user_rol, cantidad_sucursales_activas)

    return suc

@router.get("/{sucursal_id}/perfil", response_model=schemas_sucursal.SucursalPerfilOut, status_code=200)
def acceder_perfil(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.SucursalPerfilOut:

    sucursal, current_user_rol = crud_sucursal.acceder(db, sucursal_id, current_user.id) # current_user_rol en este endpoint no se usa
    
    suc = mappers_sucursal.sucursal_perfil_out(sucursal)

    return suc

# Actualizar sucursal (datos simples, teléfonos y dirección)
@router.patch("/{sucursal_id}",
    response_model=schemas_empresa.SucursalPerfilOut | schemas_sucursal.SucursalPerfilOut,
    status_code=200)
def modificar_sucursal(
    sucursal_update: schemas_sucursal.SucursalUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.SucursalPerfilOut | schemas_sucursal.SucursalPerfilOut:

    sucursal, current_user_rol = crud_sucursal.modificar(db, sucursal_id, current_user.id, sucursal_update)

    roles_de_empresa = ['PROPIETARIO', 'GERENTE_EMPRESA']

    if current_user_rol in roles_de_empresa:
        suc = mappers_empresa.sucursal_perfil_out(sucursal)
    else:
        suc = mappers_sucursal.sucursal_perfil_out(sucursal)

    return suc

@router.patch("/{sucursal_id}/desactivar", status_code=204)
def desactivar_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.desactivar(db, sucursal_id, current_user.id)

@router.patch("/{sucursal_id}/reactivar", status_code=204)
def reactivar_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.reactivar(db, sucursal_id, current_user.id)

# Devuelve todos los clientes de la sucursal según filtros (el primero devuelto será el más reciente en id)
@router.get("/{sucursal_id}/clientes", response_model=schemas_sucursal.ClientesSucursalOut, status_code=200)
def obtener_clientes(
    sucursal_id: int = Path(..., ge=1),
    search: str | None = Query(default=None, min_length=3, max_length=255, alias="busqueda"),
    activo: bool | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ClientesSucursalOut:

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    clientes, ultimo_cursor_id = crud_sucursal.obtener_clientes(
        db, sucursal_id, current_user.id, search=search, activo=activo, id_ultimo=id_ultimo, limit=limit,
    )

    clientes_out = [mappers_sucursal.cliente_out(c) for c in clientes]
    
    respuesta = schemas_sucursal.ClientesSucursalOut(
        clientes=clientes_out, # clientes_out es una lista de objetos de clase ClienteOut de Pydantic
        ultimo_cursor_id=ultimo_cursor_id,
    ) # el campo ultimo_cursor_id volverá si la sucursal pide más clientes
    
    return respuesta

@router.post("/{sucursal_id}/clientes", response_model=schemas_sucursal.ClienteOut, status_code=201)
def crear_cliente(
    cliente_nuevo: schemas_sucursal.ClienteCreate,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ClienteOut:

    cliente = crud_sucursal.crear_cliente(db, sucursal_id, current_user.id, cliente_nuevo)
    
    cliente_out = mappers_sucursal.cliente_out(cliente)

    return cliente_out

@router.patch("/{sucursal_id}/clientes/{cliente_id}", response_model=schemas_sucursal.ClienteOut, status_code=200)
def modificar_cliente(
    cliente_update: schemas_sucursal.ClienteUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ClienteOut:

    cliente = crud_sucursal.modificar_cliente(db, sucursal_id, current_user.id, cliente_id, cliente_update)

    cliente_out = mappers_sucursal.cliente_out(cliente)

    return cliente_out

@router.patch("/{sucursal_id}/clientes/{cliente_id}/desactivar", status_code=204)
def desactivar_cliente(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.desactivar_cliente(db, sucursal_id, current_user.id, cliente_id)

@router.patch("/{sucursal_id}/clientes/{cliente_id}/reactivar", status_code=204)
def reactivar_cliente(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.reactivar_cliente(db, sucursal_id, current_user.id, cliente_id)

@router.get("/{sucursal_id}/turnos", response_model=list[schemas_sucursal.TurnoSucursalOut], status_code=200)
def obtener_turnos(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_sucursal.TurnoSucursalOut]:

    turnos = crud_sucursal.obtener_turnos(db, sucursal_id, current_user.id)
    
    turnos_out = [mappers_sucursal.turno_sucursal_out(turno) for turno in turnos]

    return turnos_out

@router.post("/{sucursal_id}/turnos", response_model=schemas_sucursal.TurnoSucursalOut, status_code=201)
def reservar_turno(
    reserva: schemas_sucursal.ReservaTurnoSucursalIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.TurnoSucursalOut:

    turno = crud_sucursal.reservar_turno(db, sucursal_id, current_user.id, reserva)

    turno_out = mappers_sucursal.turno_sucursal_out(turno)

    return turno_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/{sucursal_id}/turnos/{turno_id}/estado", response_model=schemas_sucursal.TurnoSucursalOut, status_code=200)
def modificar_estado_turno(
    turno_update: schemas_sucursal.TurnoEstadoUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.TurnoSucursalOut:

    turno_modificado = crud_sucursal.modificar_estado_turno(db, sucursal_id, current_user, turno_id, turno_update)
    
    turno_out = mappers_sucursal.turno_sucursal_out(turno_modificado)

    return turno_out

@router.delete("/{sucursal_id}/turnos", status_code=204)
def eliminar_turnos(
    turnos_delete: schemas_sucursal.TurnosSucursalDeleteIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.eliminar_turnos(db, sucursal_id, current_user.id, turnos_delete.turnos, constantes.LISTA_PARCIAL_DE_ESTADOS)

@router.get("/{sucursal_id}/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def obtener_estados_turnos(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_common.TurnoEstadoOut]:

    turnos = crud_sucursal.obtener_estados_turnos(db, sucursal_id, current_user.id)

    turnos_estados = [mappers_sucursal.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que la sucursal ya completó (el primero devuelto será el más reciente)
@router.get("/{sucursal_id}/turnos/historial", response_model=schemas_sucursal.HistorialSucursalOut, status_code=200)
def obtener_historial(
    sucursal_id: int = Path(..., ge=1),
    fecha_hora_ultima: datetime | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.HistorialSucursalOut:

    # si el fecha_hora_ultima fue pasado, se toma, y si no, se toma datetime.max
    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) if fecha_hora_ultima else datetime.max

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    historial, ultimo_cursor = crud_sucursal.obtener_historial(
        db, sucursal_id, current_user.id, fecha_hora_ultima=fecha_hora_ultima, id_ultimo=id_ultimo, limit=limit,
    )

    historial_out = [mappers_sucursal.turno_historial_sucursal(h) for h in historial]
    
    respuesta = schemas_sucursal.HistorialSucursalOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialSucursal de Pydantic
        ultimo_cursor_fecha_hora=timezone.ensure_utc(ultimo_cursor[0]) if ultimo_cursor[0] else None,
        ultimo_cursor_id=ultimo_cursor[1],
    ) # los campos ultimo_cursor volverán si la sucursal pide más historial
    
    return respuesta

@router.get("/{sucursal_id}/servicios", response_model=list[schemas_sucursal.ServicioBaseOut], status_code=200)
def obtener_servicios_para_gestion(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_sucursal.ServicioBaseOut]:

    servicios = crud_sucursal.obtener_servicios_para_gestion(db, sucursal_id, current_user.id)
    
    servicios_out = [mappers_sucursal.servicio_base_out(servicio) for servicio in servicios]

    return servicios_out

@router.get("/{sucursal_id}/servicios/reserva", response_model=list[schemas_sucursal.ServicioBaseParaReservaOut], status_code=200)
def obtener_servicios_para_reserva(
    sucursal_id: int = Path(..., ge=1),
    usuario: bool = Query(...),
    cliente_email: EmailStr | None = Query(default=None, max_length=255),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_sucursal.ServicioBaseParaReservaOut]:

    if usuario:
        cliente_email = current_user.email
    elif not cliente_email:
        raise RequestValidationError([
            {
                "type": "value_error",
                "loc": ("query", "cliente_email"),
                "msg": "Debe proporcionar cliente_email si usuario=False en el router de /servicios/reserva",
            }
        ])

    servicios, turnos = crud_sucursal.obtener_servicios_para_reserva(db, cliente_email, sucursal_id, usuario)

    servicios_out = mappers_sucursal.lista_servicio_base_para_reserva_out(servicios, turnos)

    return servicios_out

@router.post("/{sucursal_id}/servicios", response_model=schemas_sucursal.ServicioBaseOut, status_code=201)
def crear_servicio_base(
    servicio_nuevo: schemas_sucursal.ServicioBaseCreate,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ServicioBaseOut:

    servicio = crud_sucursal.crear_servicio_base(db, sucursal_id, current_user.id, servicio_nuevo)
    
    servicio_out = mappers_sucursal.servicio_base_out(servicio)

    return servicio_out

@router.patch("/{sucursal_id}/servicios/{servicio_base_id}", response_model=schemas_sucursal.ServicioBaseOut, status_code=200)
def modificar_servicio_base(
    servicio_update: schemas_sucursal.ServicioBaseUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ServicioBaseOut:

    servicio = crud_sucursal.modificar_servicio_base(db, sucursal_id, current_user.id, servicio_base_id, servicio_update)
    
    servicio_out = mappers_sucursal.servicio_base_out(servicio)

    return servicio_out

@router.delete("/{sucursal_id}/servicios", status_code=204)
def eliminar_servicios_base(
    servicios_base_delete: schemas_sucursal.ServiciosBaseDeleteIn,
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.eliminar_servicios_base(db, sucursal_id, current_user.id, servicios_base_delete.servicios_base)

@router.post("/{sucursal_id}/servicios/{servicio_base_id}/versiones", response_model=schemas_sucursal.ServicioBaseOut, status_code=201)
def crear_servicio_version(
    servicio_nuevo: schemas_sucursal.ServicioCreate,
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ServicioBaseOut:

    servicio = crud_sucursal.crear_servicio_version(db, sucursal_id, current_user.id, servicio_base_id, servicio_nuevo)
    
    servicio_out = mappers_sucursal.servicio_base_out(servicio)

    return servicio_out

@router.patch("/{sucursal_id}/servicios/{servicio_base_id}/versiones/{servicio_id}",
    response_model=schemas_sucursal.ServicioOut, status_code=200)
def modificar_servicio_version(
    servicio_update: schemas_sucursal.ServicioUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    servicio_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ServicioOut:

    servicio = crud_sucursal.modificar_servicio_version(
        db,
        sucursal_id,
        current_user.id,
        servicio_base_id,
        servicio_id,
        servicio_update,
    )
    
    servicio_out = mappers_sucursal.servicio_out(servicio)

    return servicio_out

@router.delete("/{sucursal_id}/servicios/{servicio_base_id}/versiones/{servicio_id}", status_code=204)
def eliminar_servicio_version(
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    servicio_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.eliminar_servicio_version(db, sucursal_id, current_user.id, servicio_base_id, servicio_id)

@router.post("/{sucursal_id}/servicios/{servicio_base_id}/excepciones",
    response_model=schemas_sucursal.ExcepcionFechaServicioOut, status_code=201)
def crear_excepcion_fecha_servicio(
    excepcion_nueva: schemas_sucursal.ExcepcionFechaServicioCreate,
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ExcepcionFechaServicioOut:

    excepcion = crud_sucursal.crear_excepcion_fecha_servicio(
        db,
        sucursal_id,
        current_user.id,
        servicio_base_id,
        excepcion_nueva,
    )
    
    excepcion_out = mappers_sucursal.excepcion_fecha_servicio_out(excepcion)

    return excepcion_out

@router.patch("/{sucursal_id}/servicios/{servicio_base_id}/excepciones/{excepcion_id}",
    response_model=schemas_sucursal.ExcepcionFechaServicioOut, status_code=200)
def modificar_excepcion_fecha_servicio(
    excepcion_update: schemas_sucursal.ExcepcionFechaServicioUpdateIn,
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    excepcion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.ExcepcionFechaServicioOut:

    excepcion = crud_sucursal.modificar_excepcion_fecha_servicio(
        db,
        sucursal_id,
        current_user.id,
        servicio_base_id,
        excepcion_id,
        excepcion_update,
    )
    
    excepcion_out = mappers_sucursal.excepcion_fecha_servicio_out(excepcion)

    return excepcion_out

@router.delete("/{sucursal_id}/servicios/{servicio_base_id}/excepciones/{excepcion_id}", status_code=204)
def eliminar_excepcion_fecha_servicio(
    sucursal_id: int = Path(..., ge=1),
    servicio_base_id: int = Path(..., ge=1),
    excepcion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.eliminar_excepcion_fecha_servicio(db, sucursal_id, current_user.id, servicio_base_id, excepcion_id)

@router.get("/{sucursal_id}/miembros", response_model=list[schemas_sucursal.MiembroSucursalOut], status_code=200)
def obtener_miembros(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_sucursal.MiembroSucursalOut]:

    miembros = crud_sucursal.obtener_miembros(db, sucursal_id, current_user.id)
    
    miembros_out = [mappers_sucursal.miembro_sucursal_out(miembro) for miembro in miembros]

    return miembros_out

@router.delete("/{sucursal_id}/miembros/me", status_code=204)
def abandonar_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.abandonar_sucursal(db, sucursal_id, current_user.id)

# endpoint para agregar a un miembro ya de una sucursal de una empresa a otra sucursal de la misma empresa sin borrarlo de ninguna otra sucursal
# Solo lo pueden hacer los propietarios o gerentes generales
@router.post("/{sucursal_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembroSucursalOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def agregar_miembro_a_otra_sucursal(
    data: schemas_sucursal.MiembroSucursalAddIn,
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.MiembroSucursalOut:
    # miembro_sucursales es una lista de objetos Miembro_Sucursal para el mismo usuario en las distintas sucursales de la empresa
    miembro_sucursales = crud_sucursal.agregar_miembro_a_otra_sucursal(db, sucursal_id, current_user.id, target_id, data.rol)

    miembro_out = mappers_empresa.miembro_sucursal_out(miembro_sucursales)

    return miembro_out

# Solo lo pueden hacer los propietarios o gerentes generales
@router.patch("/{sucursal_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembroEmpresaOut | schemas_empresa.MiembroSucursalOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def modificar_rol(
    data: schemas_common.UpdateRolIn,
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.MiembroEmpresaOut | schemas_empresa.MiembroSucursalOut:

    miembro = crud_sucursal.modificar_rol(db, sucursal_id, current_user.id, target_id, data.nuevo_rol)

    if isinstance(miembro, models.Miembro_Empresa):
        miembro_out = mappers_empresa.miembro_empresa_out(miembro)
    if isinstance(miembro, list):
        miembro_out = mappers_empresa.miembro_sucursal_out(miembro)

    return miembro_out

@router.delete("/{sucursal_id}/miembros/{target_id}", status_code=204) # target_id es el id del miembro como usuario en la tabla usuario
def eliminar_miembro(
    sucursal_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.eliminar_miembro(db, sucursal_id, current_user.id, target_id)

@router.get("/{sucursal_id}/bloqueos", response_model=list[schemas_sucursal.BlockClienteOut], status_code=200)
def obtener_clientes_bloqueados(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_sucursal.BlockClienteOut]:

    resultados = crud_sucursal.obtener_clientes_bloqueados(db, sucursal_id, current_user.id)
    
    bloqueos_out = [mappers_sucursal.block_cliente_out(bloqueo, miembro_rol) for bloqueo, miembro_rol in resultados]

    return bloqueos_out

@router.post("/{sucursal_id}/bloqueos/{cliente_id}", response_model=schemas_sucursal.BlockClienteOut, status_code=201)
def bloquear_cliente(
    data: schemas_sucursal.BlockClienteIn,
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_sucursal.BlockClienteOut:

    bloqueo, miembro_rol = crud_sucursal.bloquear_cliente(db, sucursal_id, current_user.id, cliente_id, data.motivo)

    bloqueo_out =  mappers_sucursal.block_cliente_out(bloqueo, miembro_rol)

    return bloqueo_out

@router.delete("/{sucursal_id}/bloqueos/{cliente_id}", status_code=204)
def desbloquear_cliente(
    sucursal_id: int = Path(..., ge=1),
    cliente_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_sucursal.desbloquear_cliente(db, sucursal_id, current_user.id, cliente_id)

@router.get("/{sucursal_id}/notificaciones", response_model=schemas_common.NotificacionesOut, status_code=200)
def obtener_notificaciones(
    sucursal_id: int = Path(..., ge=1),
    leidas: bool | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_common.NotificacionesOut:

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    notificaciones, ultimo_cursor_id = crud_common.obtener_notificaciones(
        db,
        current_user.id,
        sucursal_id=sucursal_id,
        leidas=leidas,
        id_ultimo=id_ultimo,
        limit=limit,
    )
    
    respuesta = mappers_common.notificaciones_out(notificaciones, ultimo_cursor_id)
    
    return respuesta

# Cada 5 minutos el front pregunta por las notificaciones
@router.get("/{sucursal_id}/notificaciones/nuevas", response_model=list[schemas_common.NotificacionOut], status_code=200)
def obtener_notificaciones_nuevas(
    sucursal_id: int = Path(..., ge=1),
    id_posterior: int = Query(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_common.NotificacionOut]:

    notificaciones = crud_common.obtener_notificaciones_nuevas(db, current_user.id, id_posterior, sucursal_id=sucursal_id)

    notificaciones_out = [mappers_common.notificacion_out(notif) for notif in notificaciones]
    
    return notificaciones_out

@router.patch("/{sucursal_id}/notificaciones/{notificacion_id}/leida", status_code=204)
def marcar_notificacion_como_leida(
    sucursal_id: int = Path(..., ge=1),
    notificacion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:
    crud_sucursal.marcar_notificacion_como_leida(db, sucursal_id, current_user.id, notificacion_id)