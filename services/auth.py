from datetime import timedelta

from core import constantes, exceptions, config, autenticacion, mensajes
from core.database import SessionLocal
from core.logger import logger
from crud import common as crud_common

def background_forgot_password_email(email: str) -> None:

    db = SessionLocal()

    try:
        try:
            token = autenticacion.generate_password_reset_token(db, email)
        except Exception:
            db.rollback()
            logger.exception(
                "generate_password_reset_token_failed | email=%s",
                email,
            )
            return # no tiene sentido seguir

        try:
            mensajes.send_reset_email(email, token)
        except exceptions.EmailSendFailedError:
            logger.exception(
                "send_reset_email_failed | email=%s",
                email,
            )

    except Exception:
        db.rollback()
        logger.exception(
            "background_forgot_password_email_failed | email=%s",
            email,
        )
    finally:
        db.close()

def background_send_verification_email(email: str, tipo: str, token: str) -> None:
    try:
        mensajes.send_verification_email(email, tipo, token)
    except exceptions.EmailSendFailedError:
        # Ya habíamos respondido 200 OK
        logger.exception(
            "send_verification_email_failed | email=%s tipo=%s",
            email,
            tipo,
        )

def background_invitar_empleado(
    usuario_email: str,
    usuario_id: int,
    entidad_nombre: str,
    empresa_id: int,
    sucursal_id: int | None,
    cantidad_sucursales: int,
    rol: str,
) -> None:

    db = SessionLocal()

    try:
        limite_no_sobrepasado = crud_common.check_email_rate_limit(db, usuario_email, "INVITATION", limite=3)

        if not limite_no_sobrepasado:
            return

        # Crear token JWT usando create_access_token
        if sucursal_id:

            token = autenticacion.create_access_token(
                data={"usuario_id": usuario_id, "empresa_id": empresa_id, "sucursal_id": sucursal_id, "rol": rol},
                expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
            )

        else:

            token = autenticacion.create_access_token(
                data={"usuario_id": usuario_id, "empresa_id": empresa_id, "rol": rol},
                expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
            )

        try:
            if rol == 'GERENTE_EMPRESA' and cantidad_sucursales == 1:
                rol = 'Gerente'
            else:
                rol = constantes.ROL_MAP[rol]
            mensajes.send_invite_email(usuario_email, token, empresa_nombre=entidad_nombre, rol=rol)
        except exceptions.EmailSendFailedError:
            logger.exception(
                "send_invite_email_failed | email=%s",
                usuario_email,
            )

    except Exception:
        db.rollback()
        logger.exception(
            "background_invitar_empleado_failed | email=%s",
            usuario_email,
        )
    finally:
        db.close()