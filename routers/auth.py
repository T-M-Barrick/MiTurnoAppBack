from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Cookie, Response, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, selectinload
from jose import JWTError, jwt

from core import models, constantes, exceptions, config, mensajes, autenticacion, auxiliares
from core.database import get_db
from schemas import auth as schemas_auth
from services import auth as services_auth
from crud import common as crud_common
from crud import auth as crud_auth

router = APIRouter(prefix="/auth", tags=["Auth"])

# Usuario se loguea
@router.post("/login", status_code=200)
def login_usuario(
    response: Response,
    user: schemas_auth.UserLogin,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    db: Session = Depends(get_db),
):

    db_user = autenticacion.authenticate(db, user.email, user.password.get_secret_value()) # db_user es un objeto de clase Usuario de SQLAlchemy

    if not db_user:
        raise exceptions.AuthError()
    
    if not db_user.email_verificado:
        # Enviar el mail
        limite_no_sobrepasado = crud_common.check_email_rate_limit(db, db_user.email, "REGISTER")

        if limite_no_sobrepasado:

            token = autenticacion.create_email_token(
                data={"sub": db_user.id},
                expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS)
            )

            background_tasks.add_task(services_auth.background_send_verification_email, db_user.email, token)

        # damos información pero priorizamos que el usuario no se vuelva loco antes de la seguridad en este caso
        raise exceptions.UserEmailNotVerifiedError()
    
    # Crear token con duración de 1 día
    token = autenticacion.create_access_token(
        data={"sub": db_user.id},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Guardar token en cookie
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=token,
        domain=config.COOKIE_DOMAIN,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite=config.COOKIE_SAMESITE,
        max_age=60*config.ACCESS_TOKEN_EXPIRE_MINUTES)

    return {}

# Usuario cierra sesión
@router.post("/logout", status_code=204)
def logout_usuario(
    response: Response,
    token: str | None = Cookie(default=None, alias=config.COOKIE_NAME),
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):
    '''
    Mientras no se borre el historial ni las cookies del navegador (chrome por ejemplo),
    la cookie seguirá existiendo hasta que pasen ese día (24 hs).
    Entonces, si el usuario cierra y vuelve a abrir el navegador, el token seguirá estando ahí y seguirá siendo válido.
    Si la cookie se borra (por logout o por vencimiento), el backend ya no podrá validarlo → 401.
    2 usuarios distintos no pueden tener dos sesiones distintas del mismo dominio abiertas en el mismo tipo de navegador en la misma compu 
    (por más que sean 2 ventanas del mismo tipo de navegador).
    '''
    if token:
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
            jti = payload.get("jti")
            exp = datetime.fromtimestamp(payload.get("exp")) # datetime naive UTC
            crud_auth.revoke_token(db, jti=jti, expires_at=exp)
        except JWTError:
            # Token inválido o vencido → igual borramos cookie
            pass

    response.delete_cookie(
        key=config.COOKIE_NAME,
        domain=config.COOKIE_DOMAIN,
        path="/", # path por defecto suele ser "/"
        samesite=config.COOKIE_SAMESITE,
        secure=config.COOKIE_SECURE
    )

# {"message": "Contraseña modificada exitosamente"}
@router.post("/password/change", status_code=204)
def change_password(
    data: schemas_auth.ChangePassword,
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    old_password = data.old_password.get_secret_value()
    new_password = data.new_password.get_secret_value()

    crud_auth.change_password(db, current_user, old_password, new_password)

# "message": "Si el email está registrado y verificado, recibirás instrucciones para resetear tu contraseña"
@router.post("/password/forgot/email", status_code=204)
def forgot_password_email(
    solicitud: schemas_auth.ForgotPasswordEmail,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    db: Session = Depends(get_db),
):
    '''
    Desde el punto de vista del atacante:

    POST /password/forgot/email
    → 200 OK
    → {"message": "Si el email está registrado y verificado, recibirás instrucciones para resetear tu contraseña"}

    Eso pasa SIEMPRE:
    . el email exista
    . no exista
    . el token se genere
    . el email no se envíe

    La respuesta HTTP es idéntica y el BackgroundTasks hace que los tiempos sean indénticos exista o no el usuario.
    '''
    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, solicitud.email, "RESET_PASSWORD")

    if limite_no_sobrepasado:
        # Esto hace que la función termine ya, sin importar si el mail existe o no.
        background_tasks.add_task(
            services_auth.background_forgot_password_email, solicitud.email,
        )

# {"message": "Contraseña actualizada correctamente"}
@router.post("/password/reset/email", status_code=204)
def reset_password_email(
    data: schemas_auth.ResetPasswordEmail,
    db: Session = Depends(get_db),
):

    new_password = data.new_password.get_secret_value()

    autenticacion.reset_password_email(db, data.token, new_password)

# {"message": "Revisá tu teléfono para resetear la contraseña"}
@router.post("/password/forgot/mobile", status_code=204)
def forgot_password_mobile(
    solicitud: schemas_auth.ForgotPasswordMobile,
    db: Session = Depends(get_db),
):

    try:
        usuario, otp = autenticacion.generate_password_reset_otp(db=db, telefono=solicitud.telefono.numero, email=solicitud.email)

        if solicitud.forma == 'wpp':
            mensajes.enviar_otp_whatsapp(solicitud.telefono.numero, usuario.nombre, otp)
        
        elif solicitud.forma == 'sms':
            mensajes.enviar_sms(solicitud.telefono.numero, f"Tu código de recuperación de contraseña es {otp}")

    except exceptions.UserError:
        pass

    except exceptions.ForgotPasswordEmailMismatchError:
        pass

# {"message": "Contraseña actualizada correctamente"}
@router.post("/password/reset/mobile", status_code=204)
def reset_password_mobile(
    data: schemas_auth.ResetPasswordMobile,
    db: Session = Depends(get_db),
):

    new_password = data.new_password.get_secret_value()

    autenticacion.reset_password_mobile(db, telefono=data.telefono.numero, otp=data.otp, new_password=new_password)