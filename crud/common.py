from datetime import timedelta
import logging

from sqlalchemy.orm import Session, joinedload, selectinload

from core import models, constantes, exceptions, timezone, autenticacion

logger = logging.getLogger(__name__)

def get_empresa(db: Session, empresa_id: int):

    empresa = db.query(models.Empresa).options(
        joinedload(models.Empresa.direccion),
        joinedload(models.Empresa.telefonos)).filter(models.Empresa.id == empresa_id).first()

    if not empresa:
        raise exceptions.EmpresaNotFoundError()
    
    if not empresa.email_verificado:
        raise exceptions.EmpresaEmailNotVerifiedError()

    return empresa # empresa es un objeto de clase Empresa de SQLAlchemy

def verificar_rol_en_empresa(db: Session, usuario_id: int, empresa_id: int):
    """
    Verifica que un usuario pertenece a una empresa y devuelve el nombre de su rol.
    """
    miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()

    if not miembro:
        raise exceptions.EmpresaMiembroNotFoundError()
    
    rol = constantes.Rol(miembro.rol).name

    return rol # string

def nuevo_estado_check(db: Session, nuevo_estado: str, inicio_turno: datetime, duracion: int, cancelado_por_usuario: bool = True):

    if cancelado_por_usuario:
        entidad1 = 'USUARIO'
        entidad2 = 'EMPRESA'
    else:
        entidad1 = 'EMPRESA'
        entidad2 = 'USUARIO'
    
    inicio_turno = timezone.ensure_utc(turno.inicio_turno) # garantía defensiva
    ahora = timezone.now_utc()
    fin_turno = inicio_turno + timedelta(minutes=duracion)

    if nuevo_estado == 'CONFIRMADO' or nuevo_estado == f'CANCELADO_POR_{entidad2}':
        logger.warning(
            f"El Front envió mal el estado a modificar: el actor={entidad1} envió nuevo_estado={nuevo_estado}, cosa que no debería pasar"
        )
        raise exceptions.TurnoUpdateInvalidStateError(field="estado_turno")
    
    if nuevo_estado == f'CANCELADO_POR_{entidad1}':
        if ahora >= inicio_turno:
            raise exceptions.TurnoCancelTimeExpiredError(field="estado_turno")

    if nuevo_estado in ['CUMPLIDO', 'NO_CUMPLIDO']:
        if ahora < fin_turno:
            raise exceptions.TurnoNotFinishedError(field="estado_turno")

def check_email_rate_limit(db: Session, email: str, accion: str, limite: int = 5):

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    registro = db.query(models.LimiteEmail).filter_by(email=email, accion=accion).first()

    try:
        if not registro:
            registro = models.LimiteEmail(
                email=email,
                accion=accion,
                conteo=1,
                inicio_ventana=ahora_utc
            )
            db.add(registro)
            db.commit()
            return True

        # Si ya existe el registro y vuelve a comenzar el límite diario de 24 hs desde la primera vez
        if ahora_utc - registro.inicio_ventana > timedelta(days=1):
            registro.conteo = 1
            registro.inicio_ventana = ahora_utc
            db.commit()
            return True

        if registro.conteo >= limite:
            logger.warning(
                f"El correo {email} alcanzó el límite de envíos de emails para {constantes.ACCIONES_DE_ENVIO_DE_EMAIL.get(accion, accion)}"
            )
            return False

        registro.conteo += 1
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error en función check_email_rate_limit para el correo {email} para {constantes.ACCIONES_DE_ENVIO_DE_EMAIL.get(accion, accion)}: {e}"
        )
        # Si ponemos True, el usuario no quedará el registro en la tabla LimiteEmail y, por consiguiente, el usuario recibirá el mail:
        # Ventaja: el usuario no se ve perjudicado por un error en base de datos o back
        # Desventaja: Se pierde plata en envíos de mails
        # Si ponemos False, el usuario, que no tuvo la culpa, no recibirá el mail:
        # Ventaja: No se pierde plata en envíos de mails sin control
        # Desventaja: el usuario se ve perjudicado por un error en base de datos o back y no puede recibir su mail
        return False

def verificacion_email(db: Session, token: str, usuario: bool = True):

    payload = autenticacion.verify_email_token(token)
    entidad_id = payload["sub"]

    if usuario:
        entidad = db.query(models.Usuario).get(entidad_id)
        if not entidad:
            raise exceptions.UserNotFoundError()
    else:
        entidad = db.query(models.Empresa).get(entidad_id)
        if not entidad:
            raise exceptions.EmpresaNotFoundError()

    if entidad.email_verificado:
        return

    try:
        entidad.email_verificado = True
        entidad.fecha_alta = timezone.to_naive_utc(timezone.now_utc())
        db.commit()
    except Exception:
        db.rollback()
        raise