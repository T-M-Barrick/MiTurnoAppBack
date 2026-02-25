from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, exceptions, config, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import usuario as crud_usuario
from services import auth as services_auth
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario
from mappers import usuario as mappers_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
# APIRouter() crea un router, que es como una mini “sub-aplicación” dentro de FastAPI.
# prefix="/usuarios" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Usuarios"] sirve para organizar la documentación automática de Swagger (/docs).

# {"message": "Para validar su registro, le hemos enviamos un correo a su casilla con un enlace para verificar su cuenta"}
@router.post("/", status_code=201) # @router.post("/usuarios/") indica que esta función responde a POST en /usuarios/.
def create_usuario(
    user: schemas_usuario.UserCreate,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    db: Session = Depends(get_db),
):
    """
    Crea un nuevo usuario en la base de datos (registro).
    - Verifica que el email no esté ya registrado.
    - Hashea la contraseña antes de guardar.
    - Devuelve el OK en caso de éxito.
    """
    usuario = crud_usuario.create_usuario(db, user)

    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, usuario.email, "REGISTER")

    if limite_no_sobrepasado:

        token = autenticacion.create_email_token(
            data={"sub": usuario.id},
            expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS)
        )

        # DE FONDO: Para que la respuesta sea instantánea
        background_tasks.add_task(services_auth.background_send_verification_email, usuario.email, token)

    return {}

# {"message": "Correo verificado con éxito"}
@router.get("/verificacion/email", status_code=204)
def verificacion_email_usuario(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
):

    crud_common.verificacion_email(db, token)

@router.get("/me", response_model=schemas_usuario.UserLoginOut, status_code=200)
def me(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):
    '''
    Esto es para que cuando el creat o login dé el OK, el navegador pida los datos del
    usuario para el HTML del panel del usuario.
    También se usa para que el usuario entre a su panel de una cuando abra la app o dominio y ya estaba logueado y 
    el navegador ya tiene la cookie y así el usuario no tiene que poner de vuelta la contraseña y el email.
    '''
    turnos = crud_usuario.get_turnos(db, current_user.id)
    
    us = mappers_usuario.user_login_out(current_user, turnos)

    return us

# Actualizar usuario (datos simples, telefonos y direcciones)
@router.patch("/me", response_model=schemas_usuario.UserUpdateOut, status_code=200)
def update_usuario(
    user_update: schemas_usuario.UserUpdateIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    user = crud_usuario.update(db, current_user, user_update)
    
    us = mappers_usuario.user_update_out(user)

    return us

@router.get("/mis_empresas", response_model=schemas_usuario.MisEmpresasOut, status_code=200)
def get_roles(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    # Traer roles en empresas (es una lista de objetos Miembro_Empresa de SQAlchemy)
    roles_en_empresas = (
        db.query(models.Miembro_Empresa)
        .options(
            joinedload(models.Miembro_Empresa.empresa),
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
        )
        .filter(
            models.Miembro_Sucursal.usuario_id == current_user.id,
            models.Sucursal.activa == True,
        )
        .all()
    )

    empresas_out = mappers_usuario.mis_empresas_out(roles_en_empresas, roles_en_sucursales)

    return roles_empresas_out

@router.post("/turnos", response_model=schemas_usuario.TurnoUserOut, status_code=201)
def reservar_turno(
    reserva: schemas_usuario.ReservaTurnoOpcionesUserIn,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turno = crud_usuario.reservar_turno(db, current_user, reserva)

    turno_out = mappers_usuario.turno_user_out(turno)

    return turno_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/turnos/{turno_id}/estado", response_model=schemas_usuario.TurnoUserOut, status_code=200)
def update_estado_turno_usuario(
    turno_update: schemas_usuario.TurnoEstadoUpdateIn,
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turno_modificado = crud_usuario.update_estado_turno(db, current_user, turno_id, turno_update)
    
    turno_out = mappers_usuario.turno_user_out(turno_modificado)

    return turno_out

# Modifica el recordatorio de un turno de la tabla Turno y devuelve el turno con el recordatorio modificado
@router.patch("/turnos/{turno_id}/recordatorio", response_model=schemas_usuario.TurnoUserOut, status_code=200)
def update_recordatorio_turno_usuario(
    recordatorio: schemas_usuario.TurnoRecordatorioUpdateIn,
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turno_modificado = crud_usuario.update_recordatorio_turno(db, current_user.id, turno_id, recordatorio.minutos_antes)
    
    turno_out = mappers_usuario.turno_user_out(turno_modificado)

    return turno_out

@router.delete("/turnos/{turno_id}", status_code=204)
def delete_turno_usuario(
    turno_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_usuario.delete_turno(db, current_user.id, turno_id, constantes.LISTA_PARCIAL_DE_ESTADOS)

# Cada 5 minutos el front pregunta por los estados de sus turnos
@router.get("/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def get_estados_turnos_usuario(
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    turnos = crud_usuario.get_estados_turnos(db, current_user.id)

    turnos_estados = [mappers_usuario.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que el usuario ya completó (el primero devuelto será el más reciente)
@router.get("/turnos/historial", response_model=schemas_usuario.HistorialUserOut, status_code=200)
def get_historial_usuario(
    fecha_hora_ultima: datetime | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):
    
    # si el fecha_hora_ultima fue pasado, se toma, y si no, se toma datetime.max
    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) if fecha_hora_ultima else datetime.max

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    historial, ultimo_cursor = crud_usuario.get_historial(
        db, current_user.id, fecha_hora_ultima=fecha_hora_ultima, id_ultimo=id_ultimo, limit=limit,
    )
    
    historial_out = [mappers_usuario.turno_historial_user(h) for h in historial]
    
    respuesta = schemas_usuario.HistorialUserOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialUser de Pydantic
        ultimo_cursor_fecha_hora=timezone.ensure_utc(ultimo_cursor[0]) if ultimo_cursor[0] else None,
        ultimo_cursor_id=ultimo_cursor[1],
    ) # los campos ultimo_cursor volverán si el usuario pide más historial
    
    return respuesta

# Devuelve lista de sucursales (sin duplicados) con coincidencia parcial de nombre y/o rubros
# haciendo, por ejemplo, GET /usuarios/sucursales?busqueda=peluq
@router.get("/sucursales", response_model=list[schemas_usuario.SucursalOut], status_code=200)
def get_sucursales(
    search: str = Query(..., min_length=3, alias="busqueda"),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursales = crud_usuario.get_sucursales(db, search, lat, lng) # sucursales es una lista de objetos de clase Sucurusal de SQLAlchemy

    resultados = [mappers_usuario.sucursal_out(sucursal) for sucursal in sucursales]

    return resultados

# Se envía al hacer click en la sucursal
@router.get("/sucursales/{sucursal_id}/servicios", response_model=list[schemas_usuario.ServicioConTurnosOut], status_code=200)
def get_servicios_de_sucursal(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    servicios, turnos = crud_usuario.get_servicios_de_sucursal(db, current_user.email, sucursal_id)

    servicios_out = mappers_usuario.servicio_con_turnos_out(servicios, turnos)

    return servicios_out

@router.post("/sucursales/{sucursal_id}/favoritos", response_model=schemas_usuario.SucursalOut, status_code=201)
def add_favorito(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursal = crud_usuario.add_favorito(db, current_user.id, sucursal_id)
    
    sucursal_out = mappers_usuario.sucursal_out(sucursal)

    return sucursal_out

@router.delete("/sucursales/{sucursal_id}/favoritos", status_code=204)
def delete_favorito(
    sucursal_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_usuario.delete_favorito(db, current_user.id, sucursal_id)