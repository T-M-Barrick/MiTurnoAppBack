from datetime import datetime, timedelta

from core import models, constantes, exceptions, config, autenticacion, auxiliares, timezone, mensajes
from core.database import SessionLocal
from core.logger import logger
from crud import common as crud_common

def background_forgot_password_email(email: str):

    db = SessionLocal()

    try:
        token = autenticacion.generate_password_reset_token(db, email)
        mensajes.send_reset_email(email, token)
    except Exception as e:
        db.rollback()
        logger.error(
            f"Error en función background_forgot_password_email para el correo {email}: {e}"
        )
    finally:
        db.close()

def background_send_verification_email(email: str, token: str):
    try:
        mensajes.send_verification_email(email, token)
    except exceptions.EmailSendFailedError:
        # Ya habíamos respondido 200 OK
        pass

def background_invitar_empleado(
    usuario_email: str,
    usuario_id: int,
    entidad_nombre: str,
    empresa_id: int,
    sucursal_id: int | None,
    rol: str,
):

    db = SessionLocal()

    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, usuario_email, "INVITATION", limite=3)

    try:
        if limite_no_sobrepasado:

            # Crear token JWT usando create_access_token
            if sucursal_id:

                token = autenticacion.create_access_token(
                    data={"usuario_id": usuario_id, "sucursal_id": sucursal_id, "rol": rol},
                    expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
                )

            if not sucursal_id:

                token = autenticacion.create_access_token(
                    data={"usuario_id": usuario_id, "empresa_id": empresa_id, "rol": rol},
                    expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
                )

            mensajes.send_invite_email(usuario_email, token, empresa_nombre=entidad_nombre, rol=rol)

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error en función background_invitar_empleado para el usuario con correo {usuario_email}: {e}"
        )
    finally:
        db.close()