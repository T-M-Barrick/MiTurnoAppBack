from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload, selectinload

from core.logger import logger
from core import models, constantes, exceptions, timezone, autenticacion, auxiliares

def get_empresa(db: Session, empresa_id: int):

    empresa = (
        db.query(models.Empresa)
        .options(
            selectinload(models.Empresa.sucursales) # cargar sucursales para telefonos
                .selectinload(models.Sucursal.telefonos), # cargar teléfonos de cada sucursal
            selectinload(models.Empresa.sucursales) # cargar sucursales otra vez para dirección
                .joinedload(models.Sucursal.direccion), # cargar dirección de cada sucursal
        )
        .filter(models.Empresa.id == empresa_id).first()
    )

    if not empresa:
        raise exceptions.EmpresaNotFoundError()
    
    if not empresa.email_verificado:
        raise exceptions.EmpresaEmailNotVerifiedError()
    
    if not any(sucursal.activa for sucursal in empresa.sucursales):
        raise exceptions.EmpresaHasNoSucursalError()

    return empresa # empresa es un objeto de clase Empresa de SQLAlchemy

def get_sucursal(db: Session, sucursal_id: int, error_if_not_active: bool = True):

    sucursal = (
        db.query(models.Sucursal)
        .options(
            joinedload(models.Sucursal.empresa),
            selectinload(models.Sucursal.telefonos),
            joinedload(models.Sucursal.direccion),
        )
        .filter(models.Sucursal.id == sucursal_id).first()
    )

    if not sucursal:
        raise exceptions.SucursalNotFoundError()

    if error_if_not_active and not sucursal.activa:
        raise exceptions.SucursalDeactivatedError()

    return sucursal # sucursal es un objeto de clase Sucursal de SQLAlchemy

def verificar_rol_en_empresa(db: Session, usuario_id: int,
    empresa_id: int, error=exceptions.EmpresaAccessGlobalResourcesForbiddenError()):
    """
    Verifica que un usuario pertenece a una empresa y devuelve el nombre de su rol.
    """
    miembro = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.rol),
    ).filter_by(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
    ).first()

    if not miembro:
        raise error

    return miembro.rol.nombre

def verificar_rol_en_sucursal(db: Session, usuario_id: int,
    sucursal_id: int, error=exceptions.SucursalAccessResourcesForbiddenError()):
    """
    Verifica que un usuario pertenece a una sucursal sin pertenecer a la empresa global y devuelve el nombre de su rol.
    """
    miembro = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.rol),
    ).filter_by(
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    ).first()

    if not miembro:
        raise error

    return miembro.rol.nombre

def verificar_rol_en_empresa_o_sucursal(db: Session, usuario_id: int,
    empresa_id: int, sucursal_id: int, error=exceptions.EmpresaAccessResourcesForbiddenError()):
    """
    Verifica que un usuario pertenece a una sucursal (o tiene un rol más global en la empresa) y devuelve el nombre de su rol.
    """
    miembro_empresa = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.rol),
    ).filter_by(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
    ).first()

    miembro_sucursal = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.rol),
    ).filter_by(
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    ).first()

    if not miembro_empresa and not miembro_sucursal:
        raise error
    
    if miembro_empresa:
        miembro = miembro_empresa
    else:
        miembro = miembro_sucursal

    return miembro.rol.nombre

# Función para saber si una disponibilidad cubre un turno
def disponibilidad_cubre_turno(d, fecha_hora):

    dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

    if d.dia != dia:
        return False

    if not (d.hora_inicio <= hora <= d.hora_fin):
        return False

    fecha_hora_local = timezone.utc_to_local(fecha_hora) # es un datetime aware local

    # Generamos el datetime de la fecha y hora del inicio del rango de la disponibilidad (registro de la tabla Disponibilidad)
    disp_inicio_local = datetime.combine(
        fecha_hora_local.date(),
        d.hora_inicio,
        tzinfo=fecha_hora_local.tzinfo,
    ) # disp_inicio_local es un datetime aware local

    # Calculamos los minutos de diferencia entre la hora del turno que quiere sacar el usuario y la
    # hora del inicio del rango de la disponibilidad (registro de la tabla Disponibilidad)
    diferencia_minutos = int((fecha_hora_local - disp_inicio_local).total_seconds() / 60)

    return diferencia_minutos % d.intervalo == 0

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

def contar_turnos_superpuestos_servicio(db: Session, sucursal_id: int, servicio_id: int, fecha_hora: datetime, duracion: int):
    '''
    Al usar < y > en vez de <= y >=, no estoy contando los turnos pegados. Por ejemplo, si el turno nuevo comienza a las 15:00
    y hay uno que ya está sacado de 14:00 a 15:00, ese turno viejo no va a entrar en la lista y no se va a considerar superpuesto,
    siendo correcto esto ya que justo cuando termina, puede empezar uno nuevo.

    Casos de solapamiento:

    1.  Turno viejo:  [A -------- B)
        Turno nuevo:      [C -------- D)

    2.  Turno viejo:      [A -------- B)
        Turno nuevo:  [C -------- D)

    Se solapan un turno viejo con uno nuevo si y solo si se cumplen las siguientes 2 condiciones:
        . El turno viejo empieza (A) antes de que el turno nuevo termine (D): A < D
        . El turno viejo termina (B) después de que el turno nuevo empiece (C): B > C
    '''

    fecha_hora = timezone.to_naive_utc(fecha_hora)

    # Voy a contar la cantidad de turnos existentes que se superponen con el turno que el cliente quiere sacar (nuevo turno) para este servicio

    turnos = db.query(models.Turno).filter(
        models.Turno.servicio_id == servicio_id, # turno del mismo servicio
        models.Turno.estado_turno_sucursal_id == 1, # solo turnos confirmados cuento
        models.Turno.fecha_hora < fecha_hora + timedelta(minutes=duracion), # El turno existente empieza antes de que termine el nuevo turno
        models.Turno.sucursal_id == sucursal_id, # turno de la misma  sucursal (solo para confirmación del servicio)
        models.Turno.eliminado_por_sucursal == False,
    ).all()

    turnos_actuales = [
        t for t in turnos
        if t.fecha_hora + timedelta(minutes=t.duracion) > fecha_hora # el turno existente termina después de que empieza el nuevo turno
    ]

    return turnos_actuales

def tiene_turno_superpuesto(turnos: list[models.Turno], fecha_hora: datetime, duracion: int):
    '''
    Al usar < y > en vez de <= y >=, no estoy contando los turnos pegados. Por ejemplo, si el turno nuevo comienza a las 15:00
    y hay uno que ya está sacado de 14:00 a 15:00, ese turno viejo no va a entrar en la lista y no se va a considerar superpuesto,
    siendo correcto esto ya que justo cuando termina, puede empezar uno nuevo.

    Casos de solapamiento:

    1.  Turno viejo:  [A -------- B)
        Turno nuevo:      [C -------- D)

    2.  Turno viejo:      [A -------- B)
        Turno nuevo:  [C -------- D)

    Se solapan un turno viejo con uno nuevo si y solo si se cumplen las siguientes 2 condiciones:
        . El turno viejo empieza (A) antes de que el turno nuevo termine (D): A < D
        . El turno viejo termina (B) después de que el turno nuevo empiece (C): B > C
    '''

    C = timezone.to_naive_utc(fecha_hora)
    D = C + timedelta(minutes=duracion)

    for t in turnos:
        A = t.fecha_hora
        B = t.fecha_hora + timedelta(minutes=t.duracion)

        if A < D and B > C:
            return True

    return False

def check_email_rate_limit(db: Session, email: str, accion: str, limite: int = 5):

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    email_normalizado = models.normalizar_email(email)

    registro = db.query(models.LimiteEmail).filter_by(email_normalizado=email_normalizado, accion=accion).first()

    accion_nombre = constantes.ACCIONES_DE_ENVIO_DE_EMAIL.get(accion, accion)

    try:
        if not registro:
            registro = models.LimiteEmail(
                email_normalizado=email_normalizado,
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
                f"El correo {email_normalizado} alcanzó el límite de envíos de emails para {accion_nombre}"
            )
            return False

        registro.conteo += 1
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        logger.error(
            f"Error en función check_email_rate_limit para el correo {email_normalizado} para {accion_nombre}: {e}"
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
        if not entidad.sucursal:
            raise exceptions.EmpresaHasNoSucursalError()

    if entidad.email_verificado:
        return

    try:
        entidad.email_verificado = True
        entidad.fecha_hora_alta = timezone.to_naive_utc(timezone.now_utc())
        if not usuario:
            entidad.sucursal.activa = True
        db.commit()
    except Exception:
        db.rollback()
        raise

def crear_extra_data_notificacion(**metadata):
    return metadata

def guardar_notificacion(
    db: Session,
    usuario_id: int,
    tipo: str,
    extra_data: dict,
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    fecha_hora_minima_de_envio: datetime | None = None,
):

    if tipo not in constantes.NOTIFICACIONES:
        raise ValueError(f"Tipo de notificación inválido: {tipo}")
    
    ahora_naive_utc = timezone.to_naive_utc(timezone.now_utc())

    notificacion = models.Notificacion(
        usuario_id=usuario_id,
        empresa_id=empresa_id,
        sucursal_id=sucursal_id,
        tipo=tipo,
        extra_data=extra_data,
        created_at=ahora_naive_utc,
        fecha_hora_minima_de_envio=fecha_hora_minima_de_envio if fecha_hora_minima_de_envio else ahora_naive_utc,
        leida=False,
    )

    db.add(notificacion)