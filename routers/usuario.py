from datetime import datetime, timedelta
import threading

from fastapi import APIRouter, Depends, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, exceptions, config, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import usuario as crud_usuario
from services import auth as services_auth
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario
from mappers import common as mappers_common
from mappers import usuario as mappers_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
# APIRouter() crea un router, que es como una mini “sub-aplicación” dentro de FastAPI.
# prefix="/usuarios" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Usuarios"] sirve para organizar la documentación automática de Swagger (/docs).

@router.post("/", status_code=201) # @router.post("/usuarios/") indica que esta función responde a POST en /usuarios/.
def crear_usuario(
    user: schemas_usuario.UserCreate,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    db: Session = Depends(get_db),
) -> dict:
    """
    Crea un nuevo usuario en la base de datos (registro).
    - Verifica que el email no esté ya registrado.
    - Hashea la contraseña antes de guardar.
    - Devuelve el OK en caso de éxito.
    """
    usuario, usuario_ya_existia = crud_usuario.crear_usuario(db, user)

    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, usuario.email, "REGISTER")

    if limite_no_sobrepasado:

        token = autenticacion.create_email_token(
            data={"sub": usuario.id},
            expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS),
        )

        if usuario_ya_existia:

            threading.Thread(
                target=services_auth.background_send_verification_email,
                args=(usuario.email, "usuario", token),
                daemon=True,
            ).start()

        else:
            # DE FONDO: Para que la respuesta sea instantánea
            background_tasks.add_task(services_auth.background_send_verification_email, usuario.email, "usuario", token)

    if usuario_ya_existia:
        raise exceptions.UserAlreadyExistsButNotVerifiedError()
    else:
        return {}

@router.get("/verificacion/email", status_code=204)
def verificar_email(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
) -> None:

    crud_common.verificar_email(db, token)

@router.get("/me", response_model=schemas_usuario.UserLoginOut, status_code=200)
def me(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.UserLoginOut:
    '''
    Esto es para que cuando el creat o login dé el OK, el navegador pida los datos del
    usuario para el HTML del panel del usuario.
    También se usa para que el usuario entre a su panel de una cuando abra la app o dominio y ya estaba logueado y 
    el navegador ya tiene la cookie y así el usuario no tiene que poner de vuelta la contraseña y el email.
    '''
    turnos = crud_usuario.obtener_turnos(db, current_user.id)

    notificaciones, ultimo_cursor_id = crud_common.obtener_notificaciones(db, current_user.id)
    
    us = mappers_usuario.user_login_out(current_user, turnos, notificaciones, ultimo_cursor_id)

    return us

# Actualizar usuario (datos simples, telefonos y direcciones)
@router.patch("/me", response_model=schemas_usuario.UserUpdateOut, status_code=200)
def modificar_usuario(
    user_update: schemas_usuario.UserUpdateIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.UserUpdateOut:

    user = crud_usuario.modificar(db, current_user, user_update)
    
    us = mappers_usuario.user_update_out(user)

    return us

@router.get("/mis-empresas", response_model=schemas_usuario.MisEmpresasOut, status_code=200)
def obtener_roles_en_empresas_y_sucursales(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.MisEmpresasOut:

    # Traer roles en empresas (es una lista de objetos Miembro_Empresa de SQAlchemy)
    roles_en_empresas = (
        db.query(models.Miembro_Empresa)
        .options(
            joinedload(models.Miembro_Empresa.empresa),
            joinedload(models.Miembro_Empresa.rol),
        )
        .filter_by(usuario_id=current_user.id)
        .all()
    )

    # Traer roles en sucursales (es una lista de objetos Miembro_Sucursal de SQAlchemy)
    roles_en_sucursales = (
        db.query(models.Miembro_Sucursal)
        .join(models.Sucursal)
        .options(
            joinedload(models.Miembro_Sucursal.sucursal).joinedload(models.Sucursal.empresa),
            joinedload(models.Miembro_Sucursal.sucursal).joinedload(models.Sucursal.direccion),
            joinedload(models.Miembro_Sucursal.rol),
        )
        .filter(
            models.Miembro_Sucursal.usuario_id == current_user.id,
            models.Sucursal.activa == True,
        )
        .all()
    )

    roles_empresas_out = mappers_usuario.mis_empresas_out(roles_en_empresas, roles_en_sucursales)

    return roles_empresas_out

@router.post("/turnos", response_model=schemas_usuario.TurnoUserOut, status_code=201)
def reservar_turno(
    reserva: schemas_usuario.ReservaTurnoOpcionesUserIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.TurnoUserOut:

    turno = crud_usuario.reservar_turno(db, current_user, reserva)

    turno_out = mappers_usuario.turno_user_out(turno)

    return turno_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/turnos/{turno_id}/estado", response_model=schemas_usuario.TurnoUserOut, status_code=200)
def modificar_estado_turno(
    turno_update: schemas_usuario.TurnoEstadoUpdateIn,
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.TurnoUserOut:

    turno_modificado = crud_usuario.modificar_estado_turno(db, current_user, turno_id, turno_update)
    
    turno_out = mappers_usuario.turno_user_out(turno_modificado)

    return turno_out

# Modifica el recordatorio de un turno de la tabla Turno y devuelve el turno con el recordatorio modificado
@router.patch("/turnos/{turno_id}/recordatorio", response_model=schemas_usuario.TurnoUserOut, status_code=200)
def modificar_recordatorio_turno(
    recordatorio: schemas_usuario.TurnoRecordatorioUpdateIn,
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.TurnoUserOut:

    turno_modificado = crud_usuario.modificar_recordatorio_turno(db, current_user.id, turno_id, recordatorio.minutos_antes)
    
    turno_out = mappers_usuario.turno_user_out(turno_modificado)

    return turno_out

@router.delete("/turnos/{turno_id}", status_code=204)
def eliminar_turno(
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_usuario.eliminar_turno(db, current_user.id, turno_id, constantes.LISTA_PARCIAL_DE_ESTADOS)

# Cada 5 minutos el front pregunta por los estados de sus turnos
@router.get("/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def obtener_estados_turnos(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_common.TurnoEstadoOut]:

    turnos = crud_usuario.obtener_estados_turnos(db, current_user.id)

    turnos_estados = [mappers_usuario.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que el usuario ya completó (el primero devuelto será el más reciente)
@router.get("/turnos/historial", response_model=schemas_usuario.HistorialUserOut, status_code=200)
def obtener_historial(
    fecha_hora_ultima: datetime | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.HistorialUserOut:
    
    # si el fecha_hora_ultima fue pasado, se toma, y si no, se toma datetime.max
    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) if fecha_hora_ultima else datetime.max

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    historial, ultimo_cursor = crud_usuario.obtener_historial(
        db,
        current_user.id,
        fecha_hora_ultima=fecha_hora_ultima,
        id_ultimo=id_ultimo,
        limit=limit,
    )
    
    historial_out = [mappers_usuario.turno_historial_user(h) for h in historial]
    
    respuesta = schemas_usuario.HistorialUserOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialUser de Pydantic
        ultimo_cursor_fecha_hora=timezone.ensure_utc(ultimo_cursor[0]) if ultimo_cursor[0] else None,
        ultimo_cursor_id=ultimo_cursor[1],
    ) # los campos ultimo_cursor volverán si el usuario pide más historial
    
    return respuesta

# Devuelve lista de sucursales (sin duplicados) con coincidencia parcial de nombre y/o rubros
@router.get("/sucursales", response_model=list[schemas_usuario.SucursalOut], status_code=200)
def obtener_sucursales(
    search: str = Query(..., min_length=3, alias="busqueda"),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_usuario.SucursalOut]:

    lat = round(lat, 6)
    lng = round(lng, 6)

    sucursales = crud_usuario.obtener_sucursales(db, search, lat, lng)

    resultados = [mappers_usuario.sucursal_out(sucursal) for sucursal in sucursales]

    return resultados

@router.post("/sucursales/{sucursal_id}/favoritos", response_model=schemas_usuario.SucursalOut, status_code=201)
def agregar_sucursal_en_favoritos(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_usuario.SucursalOut:

    sucursal = crud_usuario.agregar_sucursal_en_favoritos(db, current_user.id, sucursal_id)
    
    sucursal_out = mappers_usuario.sucursal_out(sucursal)

    return sucursal_out

@router.delete("/sucursales/{sucursal_id}/favoritos", status_code=204)
def eliminar_sucursal_de_favoritos(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_usuario.eliminar_sucursal_de_favoritos(db, current_user.id, sucursal_id)

@router.get("/notificaciones", response_model=schemas_common.NotificacionesOut, status_code=200)
def obtener_notificaciones(
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
        leidas=leidas,
        id_ultimo=id_ultimo,
        limit=limit,
    )
    
    respuesta = mappers_common.notificaciones_out(notificaciones, ultimo_cursor_id)
    
    return respuesta

# Cada 5 minutos el front pregunta por las notificaciones
@router.get("/notificaciones/nuevas", response_model=list[schemas_common.NotificacionOut], status_code=200)
def obtener_notificaciones_nuevas(
    id_posterior: int = Query(..., ge=0),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_common.NotificacionOut]:

    notificaciones = crud_common.obtener_notificaciones_nuevas(db, current_user.id, id_posterior)

    notificaciones_out = [mappers_common.notificacion_out(notif) for notif in notificaciones]
    
    return notificaciones_out

@router.patch("/notificaciones/{notificacion_id}/leida", status_code=204)
def marcar_notificacion_como_leida(
    notificacion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:
    crud_usuario.marcar_notificacion_como_leida(db, current_user.id, notificacion_id)