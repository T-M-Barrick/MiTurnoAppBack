from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload, selectinload

from core.logger import logger
from core import models, constantes, exceptions, timezone, autenticacion

def get_empresa(db: Session, empresa_id: int) -> models.Empresa:

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

    return empresa

def get_sucursal(db: Session, sucursal_id: int, error_if_not_active: bool = True) -> models.Sucursal:

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

    return sucursal

def verificar_rol_en_empresa(
    db: Session,
    usuario_id: int,
    empresa_id: int,
    error=exceptions.EmpresaAccessGlobalResourcesForbiddenError(),
) -> str:
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

def verificar_rol_en_sucursal(
    db: Session,
    usuario_id: int,
    sucursal_id: int,
    error=exceptions.SucursalAccessResourcesForbiddenError(),
) -> str:
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

def verificar_rol_en_empresa_o_sucursal(
    db: Session,
    usuario_id: int,
    empresa_id: int,
    sucursal_id: int,
    error=exceptions.EmpresaAccessResourcesForbiddenError(),
) -> str:
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
def disponibilidad_cubre_turno(d: models.Disponibilidad, fecha_hora: datetime) -> bool:

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

def nuevo_estado_check(
    nuevo_estado: str,
    inicio_turno: datetime,
    duracion: int,
    cancelado_por_usuario: bool = True,
) -> None:

    if cancelado_por_usuario:
        entidad1 = 'USUARIO'
        entidad2 = 'EMPRESA'
    else:
        entidad1 = 'EMPRESA'
        entidad2 = 'USUARIO'
    
    inicio_turno = timezone.ensure_utc(inicio_turno) # garantía defensiva
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

def contar_turnos_superpuestos_servicio(
    db: Session,
    sucursal_id: int,
    servicio_id: int,
    fecha_hora: datetime,
    duracion: int,
) -> list[models.Turno]:
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

def tiene_turno_superpuesto(
    turnos: list[models.Turno],
    fecha_hora: datetime,
    duracion: int,
) -> bool:
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

def check_email_rate_limit(
    db: Session,
    email: str,
    accion: str,
    limite: int = 5,
) -> bool:

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
                f"El correo {email} alcanzó el límite de envíos de emails para {accion_nombre}"
            )
            return False

        registro.conteo += 1
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        logger.exception(
            "Error en función check_email_rate_limit para el correo=%s para accion=%s",
            email,
            accion_nombre,
        )
        # Si ponemos True, el usuario no quedará el registro en la tabla LimiteEmail y, por consiguiente, el usuario recibirá el mail:
        # Ventaja: el usuario no se ve perjudicado por un error en base de datos o back
        # Desventaja: Se pierde plata en envíos de mails
        # Si ponemos False, el usuario, que no tuvo la culpa, no recibirá el mail:
        # Ventaja: No se pierde plata en envíos de mails sin control
        # Desventaja: el usuario se ve perjudicado por un error en base de datos o back y no puede recibir su mail
        return False

def verificar_email(
    db: Session,
    token: str,
    usuario: bool = True,
) -> None:

    payload = autenticacion.verify_email_token(token)
    entidad_id = int(payload["sub"])

    if usuario:
        entidad = db.query(models.Usuario).get(entidad_id)
        if not entidad:
            raise exceptions.UserNotFoundError()
    else:
        entidad = db.query(models.Empresa).get(entidad_id)
        if not entidad:
            raise exceptions.EmpresaNotFoundError()
        
        sucursal = db.query(models.Sucursal).filter(models.Sucursal.empresa_id == entidad_id).first()
        if not sucursal:
            raise exceptions.EmpresaHasNoSucursalError()

    if entidad.email_verificado:
        return

    try:
        entidad.email_verificado = True
        entidad.fecha_hora_alta = timezone.to_naive_utc(timezone.now_utc())
        if not usuario:
            sucursal.activa = True
        db.commit()
    except Exception:
        db.rollback()
        raise

'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /usuarios/notificaciones?leidas=false&id_ultimo=1234&limit=20
GET /empresas/5/notificaciones?leidas=false&id_ultimo=1234&limit=20
GET /sucursales/5/notificaciones?leidas=false&id_ultimo=1234&limit=20
'''
def obtener_notificaciones(
    db: Session,
    usuario_id: int,
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    leidas: bool | None = None,
    id_ultimo: int | None = None,
    limit: int = 20,
) -> tuple[list[models.Notificacion], int | None]:
    '''
    Devuelve las notificaciones de un usuario (puede ser como cliente, como miembro de empresa o como miembro de sucursal) con paginación.
    Van ordenadas de la más reciente a la más antigua (fecha descendente).

    Parámetros:
        leidas: si es None, devuelve tanto las leidas como las no leidas.
        id_ultimo: id de la última notificación recibida (para la siguiente página).
        limit: cantidad máxima de notificaciones a devolver (máx 100).
    
    Proceso:
        Primera solicitud (en login): front no envía cursor → back devuelve primeros N registros + cursor del último.
        Siguientes solicitudes: front envía cursor → back devuelve los siguientes N registros + cursor actualizado.
        Última página: back devuelve lista vacía y cursor None → front deja de pedir más.
    '''

    if empresa_id and sucursal_id:
        raise ValueError("No se puede enviar empresa_id y sucursal_id juntos para la función obtener_notificaciones")

    query = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
    )

    if empresa_id:
        get_empresa(db, empresa_id)
        verificar_rol_en_empresa(db, usuario_id, empresa_id)

        query = query.filter(models.Notificacion.empresa_id == empresa_id)

    elif sucursal_id:
        get_sucursal(db, sucursal_id)
        verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

        query = query.filter(models.Notificacion.sucursal_id == sucursal_id)

    else: # como cliente
        query = query.filter(
            models.Notificacion.empresa_id.is_(None),
            models.Notificacion.sucursal_id.is_(None),
        )

    # Aplicar paginación por cursor si se envió id_ultimo
    if id_ultimo:
        query = query.filter(models.Notificacion.id < id_ultimo)
    
    # Filtro por leidas (IMPORTANTE usar is not None)
    if leidas is not None:
        query = query.filter(models.Notificacion.leida == leidas)

    query = query.order_by(models.Notificacion.id.desc())

    limit = min(limit, 100) # no más de 100 por consulta

    # notificaciones es una lista de objetos de clase Notificacion de SQLAlchemy
    notificaciones = query.limit(limit).all()

    ultimo_cursor_id = notificaciones[-1].id if notificaciones else None

    return notificaciones, ultimo_cursor_id

def obtener_notificaciones_nuevas(
    db: Session,
    usuario_id: int,
    id_posterior: int,
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
) -> list[models.Notificacion]:

    if empresa_id and sucursal_id:
        raise ValueError("No se puede enviar empresa_id y sucursal_id juntos para la función obtener_notificaciones_nuevas")

    query = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
        models.Notificacion.id > id_posterior,
    )

    if empresa_id:
        get_empresa(db, empresa_id)
        verificar_rol_en_empresa(db, usuario_id, empresa_id)

        query = query.filter(models.Notificacion.empresa_id == empresa_id)

    elif sucursal_id:
        get_sucursal(db, sucursal_id)
        verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

        query = query.filter(models.Notificacion.sucursal_id == sucursal_id)

    else: # como cliente
        query = query.filter(
            models.Notificacion.empresa_id.is_(None),
            models.Notificacion.sucursal_id.is_(None),
        )
    
    notificaciones_nuevas = query.order_by(models.Notificacion.id.desc()).all()

    return notificaciones_nuevas

def crear_extra_data_notificacion(**metadata) -> dict:
    return metadata

def guardar_notificacion(
    db: Session,
    usuario_id: int,
    tipo: str,
    extra_data: dict,
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    fecha_hora_minima_de_envio: datetime | None = None,
) -> None:

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