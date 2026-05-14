from datetime import timedelta
import threading

from fastapi import APIRouter, Depends, UploadFile, File, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, exceptions, config, autenticacion
from core.database import get_db
from crud import common as crud_common
from crud import empresa as crud_empresa
from services import auth as services_auth
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa
from mappers import common as mappers_common
from mappers import empresa as mappers_empresa

router = APIRouter(prefix="/empresas", tags=["Empresas"])
# APIRouter() crea un router, que es como una mini “sub-aplicación” dentro de FastAPI.
# prefix="/empresas" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Empresas"] sirve para organizar la documentación automática de Swagger (/docs).

@router.post("/", status_code=201) # @router.post("/empresas/") indica que esta función responde a POST en /empresas/.
def crear_empresa(
    empresa_nueva: schemas_empresa.EmpresaCreate,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> dict:

    empresa, empresa_ya_existia = crud_empresa.crear(db, current_user.id, empresa_nueva)

    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, empresa.email, "REGISTER")

    if limite_no_sobrepasado:

        token = autenticacion.create_email_token(
            data={"sub": empresa.id},
            expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS),
        )

        if empresa_ya_existia:

            threading.Thread(
                target=services_auth.background_send_verification_email,
                args=(empresa.email, "empresa", token),
                daemon=True,
            ).start()

        else:
            # DE FONDO: Para que la respuesta sea instantánea
            background_tasks.add_task(services_auth.background_send_verification_email, empresa.email, "empresa", token)

    if empresa_ya_existia:
        raise exceptions.EmpresaAlreadyExistsButNotVerifiedError()
    else:
        return {}

@router.get("/verificacion/email", status_code=204)
def verificar_email(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
) -> None:

    crud_common.verificar_email(db, token, usuario=False)

@router.get("/{empresa_id}/panel", response_model=schemas_empresa.EmpresaHomeOut, status_code=200)
def acceder_panel(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.EmpresaHomeOut:

    empresa, current_user_rol = crud_empresa.acceder(db, empresa_id, current_user.id)

    if not empresa.email_verificado and current_user_rol == 'PROPIETARIO':

        limite_no_sobrepasado = crud_common.check_email_rate_limit(db, empresa.email, "REGISTER")

        if limite_no_sobrepasado:

            token = autenticacion.create_email_token(
                data={"sub": empresa.id},
                expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS),
            )

            # Agregar a threading.Thread para no bloquear la respuesta
            '''
            Se usa un hilo threading.Thread en lugar de background_tasks porque después de enviar el email, el endpoint lanza
            una excepción (EmpresaVerificationEmailResentError) en lugar de retornar una respuesta normal. BackgroundTasks en FastAPI
            ejecuta las tareas después de que la respuesta es enviada — está ligado al ciclo de vida de la respuesta exitosa.
            Cuando el endpoint lanza una excepción, FastAPI pasa por el exception handler y manda una respuesta de error.
            Las background tasks registradas en ese request no se ejecutan. threading.Thread en cambio es fire-and-forget
            puro — se lanza independientemente de lo que pase con la respuesta HTTP, así que el email se envía igual aunque
            el endpoint termine en excepción.
            '''
            threading.Thread(
                target=services_auth.background_send_verification_email,
                args=(empresa.email, "empresa", token),
                daemon=True,
            ).start()
        
        raise exceptions.EmpresaVerificationEmailResentError()

    notificaciones, ultimo_cursor_id = crud_common.obtener_notificaciones(db, current_user.id, empresa_id=empresa_id)
    
    emp = mappers_empresa.empresa_home_out(empresa, notificaciones, ultimo_cursor_id, current_user_rol)

    return emp

@router.get("/{empresa_id}/perfil", response_model=schemas_empresa.EmpresaPerfilOut, status_code=200)
def acceder_perfil(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.EmpresaPerfilOut:

    empresa, current_user_rol = crud_empresa.acceder(db, empresa_id, current_user.id)
    
    emp = mappers_empresa.empresa_perfil_out(empresa, empresa.sucursales)

    return emp

# Actualizar empresa (datos simples)
@router.patch("/{empresa_id}", response_model=schemas_empresa.EmpresaPerfilOut, status_code=200)
def modificar_empresa(
    empresa_update: schemas_empresa.EmpresaUpdateIn,
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.EmpresaPerfilOut:

    empresa, current_user_rol = crud_empresa.modificar(db, empresa_id, current_user.id, empresa_update)

    emp = mappers_empresa.empresa_perfil_out(empresa, [])

    return emp

@router.patch("/{empresa_id}/logo", response_model=schemas_empresa.EmpresaLogoOut, status_code=200)
def modificar_logo(
    empresa_id: int = Path(..., ge=1),
    file: UploadFile | None = File(default=None),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.EmpresaLogoOut:

    logo_url = crud_empresa.modificar_logo(db, empresa_id, current_user.id, file)

    logo_out = mappers_empresa.empresa_logo_out(logo_url)

    return logo_out

@router.get("/{empresa_id}/miembros", response_model=schemas_empresa.MiembrosEmpresaOut, status_code=200)
def obtener_miembros(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.MiembrosEmpresaOut:

    miembros_empresa, miembros_sucursales = crud_empresa.obtener_miembros(db, empresa_id, current_user.id)
    
    miembros_out = mappers_empresa.miembros_empresa_out(miembros_empresa, miembros_sucursales)

    return miembros_out

@router.patch("/{empresa_id}/miembros/me", response_model=schemas_empresa.MiembroEmpresaOut, status_code=200)
def modificar_rol_personal(
    data: schemas_common.UpdateRolIn,
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.MiembroEmpresaOut:

    miembro = crud_empresa.modificar_rol(db, empresa_id, current_user.id, current_user.id, data.nuevo_rol, data.sucursal_id)

    miembro_out = mappers_empresa.miembro_empresa_out(miembro)

    return miembro_out

@router.delete("/{empresa_id}/miembros/me", status_code=204)
def abandonar_empresa(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_empresa.abandonar_empresa(db, empresa_id, current_user.id)

@router.patch("/{empresa_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembroEmpresaOut | schemas_empresa.MiembroSucursalOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def modificar_rol(
    data: schemas_common.UpdateRolIn,
    empresa_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> schemas_empresa.MiembroEmpresaOut | schemas_empresa.MiembroSucursalOut:

    miembro = crud_empresa.modificar_rol(db, empresa_id, current_user.id, target_id, data.nuevo_rol, data.sucursal_id)

    if isinstance(miembro, models.Miembro_Empresa):
        miembro_out = mappers_empresa.miembro_empresa_out(miembro)
    if isinstance(miembro, list):
        miembro_out = mappers_empresa.miembro_sucursal_out(miembro)

    return miembro_out

@router.delete("/{empresa_id}/miembros/{target_id}", status_code=204) # target_id es el id del miembro como usuario en la tabla usuario
def eliminar_miembro(
    empresa_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_empresa.eliminar_miembro(db, empresa_id, current_user.id, target_id)

@router.get("/{empresa_id}/notificaciones", response_model=schemas_common.NotificacionesOut, status_code=200)
def obtener_notificaciones(
    empresa_id: int = Path(..., ge=1),
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
        empresa_id=empresa_id,
        leidas=leidas,
        id_ultimo=id_ultimo,
        limit=limit,
    )
    
    respuesta = mappers_common.notificaciones_out(notificaciones, ultimo_cursor_id)
    
    return respuesta

# Cada 5 minutos el front pregunta por las notificaciones
@router.get("/{empresa_id}/notificaciones/nuevas", response_model=list[schemas_common.NotificacionOut], status_code=200)
def obtener_notificaciones_nuevas(
    empresa_id: int = Path(..., ge=1),
    id_posterior: int = Query(..., ge=0),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> list[schemas_common.NotificacionOut]:

    notificaciones = crud_common.obtener_notificaciones_nuevas(db, current_user.id, id_posterior, empresa_id=empresa_id)

    notificaciones_out = [mappers_common.notificacion_out(notif) for notif in notificaciones]
    
    return notificaciones_out

@router.patch("/{empresa_id}/notificaciones/{notificacion_id}/leida", status_code=204)
def marcar_notificacion_como_leida(
    empresa_id: int = Path(..., ge=1),
    notificacion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    crud_empresa.marcar_notificacion_como_leida(db, empresa_id, current_user.id, notificacion_id)