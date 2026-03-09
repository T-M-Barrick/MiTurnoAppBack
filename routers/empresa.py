from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, UploadFile, File, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, exceptions, config, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import empresa as crud_empresa
from services import auth as services_auth
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa
from mappers import empresa as mappers_empresa

router = APIRouter(prefix="/empresas", tags=["Empresas"])
# APIRouter() crea un router, que es como una mini “sub-aplicación” dentro de FastAPI.
# prefix="/empresas" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Empresas"] sirve para organizar la documentación automática de Swagger (/docs).

# {"message": "Para validar el registro de su empresa, le hemos enviamos un correo a la casilla del email de la empresa con un enlace para su verificación"}
@router.post("/", status_code=201) # @router.post("/empresas/") indica que esta función responde a POST en /empresas/.
def create_empresa(
    empresa_nueva: schemas_empresa.EmpresaCreate,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    empresa = crud_empresa.create(db, current_user.id, empresa_nueva) # Devuelve un objeto de clase Empresa de SQLAlchemy

    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, empresa.email, "REGISTER")

    if limite_no_sobrepasado:

        token = autenticacion.create_email_token(
            data={"sub": empresa.id},
            expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS)
        )

        # DE FONDO: Para que la respuesta sea instantánea
        background_tasks.add_task(services_auth.background_send_verification_email, empresa.email, token)
    
    return {}

# {"message": "Correo verificado con éxito"}
@router.get("/verificacion/email", status_code=204)
def verificacion_email_empresa(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
):

    crud_common.verificacion_email(db, token, usuario=False)

@router.get("/{empresa_id}/panel", response_model=schemas_empresa.EmpresaHomeOut, status_code=200)
def acceder_empresa(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    empresa, current_user_rol = crud_empresa.acceder(db, empresa_id, current_user.id)

    notificaciones, ultimo_cursor_id = crud_empresa.get_notificaciones(db, empresa_id, current_user.id)
    
    emp = mappers_empresa.empresa_home_out(empresa, notificaciones, ultimo_cursor_id, current_user_rol)

    return emp

@router.get("/{empresa_id}/perfil", response_model=schemas_empresa.EmpresaPerfilOut, status_code=200)
def acceder_perfil_empresa(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    empresa, current_user_rol = crud_empresa.acceder(db, empresa_id, current_user.id)
    
    emp = mappers_empresa.empresa_perfil_out(empresa, current_user_rol)

    return emp

# Actualizar empresa (datos simples)
@router.patch("/{empresa_id}", response_model=schemas_empresa.EmpresaHomeOut, status_code=200)
def update_empresa(
    empresa_update: schemas_empresa.EmpresaUpdateIn,
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    empresa, current_user_rol = crud_empresa.update(db, empresa_id, current_user.id, empresa_update)

    emp = mappers_empresa.empresa_home_out(empresa, [], None, current_user_rol)

    return emp

@router.patch("/{empresa_id}/logo", response_model=schemas_empresa.EmpresaLogoOut, status_code=200)
def update_empresa_logo(
    empresa_id: int = Path(..., ge=1),
    file: UploadFile | None = File(default=None),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    logo_url = crud.update_logo(db, empresa_id, file)

    logo_out = mappers_empresa.empresa_logo_out(logo_url)

    return logo_out

@router.get("/{empresa_id}/sucursales/desactivadas", response_model=list[schemas_empresa.SucursalPerfilOut], status_code=200)
def get_sucursales_desactivadas(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    sucursales = crud_empresa.get_sucursales_desactivadas(db, empresa_id, current_user.id)

    sucursales_out = [mappers_empresa.sucursal_perfil_out(sucursal) for sucursal in sucursales]
    
    return sucursales_out

@router.get("/{empresa_id}/miembros", response_model=schemas_empresa.MiembrosEmpresaOut, status_code=200)
def get_miembros_empresa(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    miembros_empresa, miembros_sucursales = crud_empresa.get_miembros(db, empresa_id, current_user.id)
    
    miembros_out = mappers_empresa.miembros_empresa_out(miembros_empresa, miembros_sucursales)

    return miembros_out

@router.patch("/{empresa_id}/miembros/me", response_model=schemas_empresa.MiembroEmpresaOut, status_code=200)
def update_personal_rol(
    data: schemas_common.UpdateRolIn,
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    miembro = crud_empresa.update_rol(db, empresa_id, current_user.id, current_user.id, data.nuevo_rol, data.sucursal_id)

    miembro_out = mappers_empresa.miembro_empresa_out(miembro)

    return miembro_out

@router.delete("/{empresa_id}/miembros/me", status_code=204)
def leave_empresa(
    empresa_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_empresa.leave_empresa(db, empresa_id, current_user.id)

# "message": f"Rol de {apellido}, {nombre} modificado a {nuevo_rol}"
@router.patch("/{empresa_id}/miembros/{target_id}",
    response_model=schemas_empresa.MiembrosEmpresaOut,
    status_code=200) # target_id es el id del miembro como usuario en la tabla usuario
def update_rol(
    data: schemas_common.UpdateRolIn,
    empresa_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    miembro = crud_empresa.update_rol(db, empresa_id, current_user.id, target_id, data.nuevo_rol, data.sucursal_id)

    if isinstance(miembro, models.Miembro_Empresa):
        miembro_out = mappers_empresa.miembros_empresa_out([miembro], [])
    if isinstance(miembro, list[models.Miembro_Sucursal]):
        miembro_out = mappers_empresa.miembros_empresa_out([], miembro)

    return miembro_out

# {"message": f"{apellido}, {nombre} fue eliminado correctamente de esta empresa"}
@router.delete("/{empresa_id}/miembros/{target_id}", status_code=204) # target_id es el id del miembro como usuario en la tabla usuario
def delete_miembro(
    empresa_id: int = Path(..., ge=1),
    target_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    crud_empresa.delete_miembro(db, empresa_id, current_user.id, target_id)

@router.get("/{empresa_id}/notificaciones", response_model=schemas_common.NotificacionesOut, status_code=200)
def get_notificaciones_empresa(
    empresa_id: int = Path(..., ge=1),
    leidas: bool | None = Query(default=None),
    id_ultimo: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100, alias="limite"),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    id_ultimo = id_ultimo if id_ultimo else 2**31 - 1 # valor grande si no viene

    notificaciones, ultimo_cursor_id = crud_empresa.get_notificaciones(
        db,
        empresa_id,
        current_user.id,
        leidas=leidas,
        id_ultimo=id_ultimo,
        limit=limit,
    )
    
    respuesta = mappers_common.notificaciones_out(notificaciones, ultimo_cursor_id)
    
    return respuesta

# Cada 5 minutos el front pregunta por las notificaciones
@router.get("/{empresa_id}/notificaciones/nuevas", response_model=list[schemas_common.NotificacionOut], status_code=200)
def get_notificaciones_nuevas_empresa(
    empresa_id: int = Path(..., ge=1),
    id_posterior: int = Query(..., ge=1),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    notificaciones = crud_empresa.get_notificaciones_nuevas(db, empresa_id, current_user.id, id_posterior)

    notificaciones_out = [mappers_common.notificacion_out(notif) for notif in notificaciones]
    
    return notificaciones_out

@router.patch("/{empresa_id}/notificaciones/{notificacion_id}/leida", status_code=204)
def update_notificacion_leida_empresa(
    empresa_id: int = Path(..., ge=1),
    notificacion_id: int = Path(..., ge=1),
    current_user: models.Usuario = Depends(...),
    db: Session = Depends(get_db),
):
    crud_empresa.update_notificacion_leida(db, empresa_id, current_user.id, notificacion_id)