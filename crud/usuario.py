import random
from datetime import date, time, datetime, timedelta

from jose import jwt
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import get_empresa, nuevo_estado_check
from core import models, constantes, exceptions, autenticacion, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario

# Crear usuario
def create_usuario(db: Session, user: schemas_usuario.UserCreate):

    # Verificar si el email ya existe
    usuario_existe = db.query(models.Usuario).filter_by(email=user.email).first()
    if usuario_existe:
        return usuario_existe

    try:
        # Crear el objeto de usuario
        db_user = models.Usuario(
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,
            email_verificado=False,
            hashed_password=autenticacion.get_password_hash(user.password))

        db.add(db_user)
        db.flush()

        # Agregar teléfonos
        for t in user.telefonos:
            db_tel = models.Telefono(numero=t.numero, usuario_id=db_user.id)
            db.add(db_tel)

        # Agregar direcciones
        for d in user.direcciones:
            db_dir = models.Direccion(
                calle=d.calle,
                altura=d.altura,
                localidad=d.localidad,
                departamento=d.departamento,
                provincia=d.provincia,
                pais=d.pais,
                lat=d.lat,
                lng=d.lng,
                aclaracion=d.aclaracion)

            db.add(db_dir)
            db.flush()

            # Registrar relación en tabla intermedia
            dir_user = models.Dir_Usuario(direccion_id=db_dir.id, usuario_id=db_user.id)
            db.add(dir_user)

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    return db_user

def get_turnos(db: Session, usuario_id: int):
    '''
    Devuelve todos los turnos de un usuario que aparecen en la tabla turno: los futuros y los pasados que el usuario no eliminó.
    Van ordenados del más antiguo al más lejano (fecha descendente).
    '''

    query = db.query(models.Turno).filter(models.Turno.usuario_id == usuario_id,
                                            or_(models.Turno.eliminado == None, models.Turno.eliminado == 's'))  # Debe ser NULL o 's'
    
    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Turno
    query = query.options(
        joinedload(models.Turno.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion), # Empresa relacionada
        joinedload(models.Turno.estado_turno_usuario) # Estado del turno del usuario
    )
    
    # Los que tienen fecha más antigua aparecerán más arriba que los de fecha más futura en el tiempo
    turnos = query.order_by(models.Turno.fecha_hora.asc()).all()

    return turnos # turnos es una lista de objetos de clase Turno de SQLAlchemy

# Actualizar usuario
def update(db: Session, user: models.Usuario, user_update: schemas_usuario.UserUpdateIn):
    '''
    1. Actualiza los datos simples del usuario (dni, nombre, etc.).

    2. Actualiza teléfonos usando una lista de TelefonoConID [[id, numero], ...]:

        .Si id es 0 → crea nuevo.

        .Si existe → actualiza su número.

        .Si un teléfono que estaba en BD no aparece en la lista → lo elimina.

    3. Actualiza direcciones con DireccionUpdateIn.
    '''

    try:
        # ----------------------------
        # 1️⃣ Actualizar campos simples
        # ----------------------------

        # Con user_update.dict(exclude_unset=True) convierto al schema temporalmente en diccionario excluyendo los campos del schema que no fueron enviados en el JSON
        for attr, value in user_update.dict(exclude_unset=True).items():
            if attr not in ["telefonos", "direcciones"]:
                # setattr(objeto, atributo, valor) es una función de Python que asigna dinámicamente un valor a un atributo de un objeto
                # en lugar de hacer user.apellido = "Fernández" o user.nombre = "Tomás" que es menos dinámico para este bucle
                setattr(user, attr, value)

        # ----------------------------
        # 2️⃣ Actualizar TELÉFONOS
        # ----------------------------

        # user_update sigue siendo un ojeto de la clase schema UserUpdateIn
        if user_update.telefonos is not None:
            current_phones = {t.id: t for t in user.telefonos}
            new_ids = set()

            for tel in user_update.telefonos: # tel es un objeto de la clase schema TelefonoConID

                if tel.id and tel.id in current_phones:
                    # Actualizar teléfono existente
                    db_tel = current_phones[tel.id]
                    db_tel.numero = tel.numero
                    new_ids.add(tel.id)
                else:
                    # Crear nuevo teléfono
                    new_tel = models.Telefono(numero=tel.numero, usuario_id=user.id)
                    db.add(new_tel)

            # Eliminar teléfonos que ya no están en la lista
            for old_id in list(current_phones.keys()):
                if old_id not in new_ids:
                    tel = db.query(models.Telefono).filter(models.Telefono.id == old_id).first()
                    if tel:
                        db.delete(tel)

        # ----------------------------
        # 3️⃣ Actualizar DIRECCIONES
        # ----------------------------
        if user_update.direcciones is not None:
            current_dirs = {
                du.direccion_id: du.direccion
                for du in db.query(models.Dir_Usuario)
                            .options(joinedload(models.Dir_Usuario.direccion))
                            .filter(models.Dir_Usuario.usuario_id == user.id)
                            .all()
            }
            new_dir_ids = set()

            for d in user_update.direcciones:
                if d.id and d.id in current_dirs:
                    db_dir = current_dirs[d.id]
                    db_dir.calle = d.calle
                    db_dir.altura = d.altura
                    db_dir.localidad = d.localidad
                    db_dir.departamento = d.departamento
                    db_dir.provincia = d.provincia
                    db_dir.pais = d.pais
                    db_dir.lat = d.lat
                    db_dir.lng = d.lng
                    db_dir.aclaracion = d.aclaracion
                    new_dir_ids.add(d.id)
                else:
                    # Crear nueva dirección
                    db_dir = models.Direccion(
                        calle=d.calle,
                        altura=d.altura,
                        localidad=d.localidad,
                        departamento=d.departamento,
                        provincia=d.provincia,
                        pais=d.pais,
                        lat=d.lat,
                        lng=d.lng,
                        aclaracion=d.aclaracion
                    )
                    db.add(db_dir)
                    db.flush()
                    db.add(models.Dir_Usuario(direccion_id=db_dir.id, usuario_id=user.id))

            # Eliminar direcciones eliminadas
            for old_id in list(current_dirs.keys()):
                if old_id not in new_dir_ids:
                    dir_usuario = db.query(models.Dir_Usuario).filter_by(direccion_id=old_id, usuario_id=user.id).first()
                    if dir_usuario:
                        db.delete(dir_usuario)
                        db.flush()
                    # Eliminar dirección si nadie más la usa
                    used = db.query(models.Dir_Usuario).filter(models.Dir_Usuario.direccion_id == old_id).count()
                    if used == 0:
                        direccion = db.query(models.Direccion).filter(models.Direccion.id == old_id).first()
                        if direccion:
                            db.delete(direccion)

        db.commit()

    except Exception:
        db.rollback()
        raise

    user = (
        db.query(models.Usuario)
        .options(
            joinedload(models.Usuario.telefonos),
            joinedload(models.Usuario.direcciones))
        .filter(models.Usuario.id == user.id).first()
    )
    return user # user es un objeto de clase Usuario de SQLAlchemy

def get_turno(db: Session, turno_id: int):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion),
        joinedload(models.Turno.estado_turno_usuario),
        joinedload(models.Turno.recordatorio)).filter(models.Turno.id == turno_id).first()
    
    return turno

def contar_turnos_superpuestos(db: Session, empresa_id: int, servicio_id: int, fecha_hora: datetime, duracion: int):

    fecha_hora = timezone.to_naive_utc(fecha_hora)

    # Voy a contar la cantidad de turnos existentes que se superponen con el turno que el cliente quiere sacar (nuevo turno) para este servicio

    turnos = db.query(models.Turno).filter(
        models.Turno.empresa_id == empresa_id, # turno de la misma empresa
        models.Turno.servicio_id == servicio_id, # turno del mismo servicio
        models.Turno.fecha_hora < fecha_hora + timedelta(minutes=duracion), # El turno existente empieza antes de que termine el nuevo turno
        models.Turno.estado_turno_empresa_id == 1 # solo turnos confirmados cuento
        ).all()

    turnos_actuales = [
        t for t in turnos
        if t.fecha_hora + timedelta(minutes=t.duracion) > fecha_hora # el turno existente termina después de que empieza el nuevo turno
    ]

    return turnos_actuales

def tiene_turno_superpuesto(turnos: list[models.Turno], fecha_hora: datetime, duracion: int):
    '''
    Casos de solapamiento:

    1.  Turno viejo:  [A -------- B]
        Turno nuevo:      [C -------- D]

    2.  Turno viejo:      [A -------- B]
        Turno nuevo:  [C -------- D]

    Se solapan un turno viejo con uno nuevo si y solo si se cumplen las siguientes 2 condiciones:
        . El turno viejo empieza (A) antes de que el turno nuevo termine (D): A < D
        . El turno viejo termina (B) después de que el turno nuevo empiece (C): B > C
    '''

    C = timezone.to_naive_utc(fecha_hora)
    D = fecha_hora + timedelta(minutes=duracion)

    for t in turnos:
        A = t.fecha_hora
        B = t.fecha_hora + timedelta(minutes=t.duracion)

        if A < D and B > C:
            return True

    return False

def mapear_error_en_reserva_turno(errores_en_servicios, clase_error):
    '''
    Lo malo que tiene esta función es que si hay algo de metada en las excepciones y hay
    dos o más excepciones de igual clase pero distinta metada, devolverá la primera
    que encuentre, haciendo que especifique la metadata de uno solo de los servicios. Es algo muy menor pero vale aclararlo.
    '''
    for error in errores_en_servicios:
        if isinstance(error, clase_error):
            raise error

def reservar_turno(db: Session, usuario_id: int, reserva: schemas_usuario.ReservaTurnoOpcionesIn, recordatorio_minutos_antes: int | None):

    # Traer empresa y servicio
    turnos_posibles = reserva.opciones # lista de ReservaTurnoIn

    empresa_id = turnos_posibles[0].empresa_id # tomamos el primero, total los empresa_id son todos iguales

    fecha_hora = turnos_posibles[0].fecha_hora # tomamos el primero, total los fecha_hora son todos iguales

    # Traer empresa y servicio
    get_empresa(db, empresa_id)

    bloqueo = db.query(models.Empresa_Bloqueo).filter_by(empresa_id=empresa_id, usuario_id=usuario_id).first()
    if bloqueo:
        raise EmpresaUserBlockedError()

    dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

    turnos_actuales_usuario = db.query(models.Turno).filter_by(
        usuario_id=usuario_id, estado_turno_usuario_id=1 # solo turnos confirmados cuento
    ).all()

    errores_en_servicios = []
    servicios_posibles = [] # lista de objetos Servicio

    for turno_posible in turnos_posibles:

        servicio = (
            db.query(models.Servicio)
            .filter(
                models.Servicio.id == turno_posible.servicio_id,
                models.Servicio.empresa_id == turno_posible.empresa_id
            )
            .first()
        )

        if not servicio:
            errores_en_servicios.append(exceptions.EmpresaServiceNotFoundError())
            continue

        servicio = (
            db.query(models.Servicio)
            .join(models.Disponibilidad)
            .options(joinedload(models.Servicio.profesional), selectinload(models.Servicio.disponibilidades))
            .filter(
                models.Servicio.id == turno_posible.servicio_id,
                models.Servicio.empresa_id == turno_posible.empresa_id,
                models.Disponibilidad.dia == dia,
                models.Disponibilidad.hora_inicio <= hora,
                models.Disponibilidad.hora_fin > hora
            )
            .first()
        )

        if not servicio:
            errores_en_servicios.append(exceptions.TurnoReservaDisponibilidadNoConfiguradaError())
            continue
        
        # Validar límite máximo de días
        if servicio.dias_max_reserva is not None:
            validar_turno_dias_max = timezone.validar_turno_dias_max(fecha_hora, servicio.dias_max_reserva)
            if not validar_turno_dias_max:
                errores_en_servicios.append(exceptions.TurnoReservaFueraDeRangoError(dias_max=servicio.dias_max_reserva))
                continue

        # Validar anticipación para reserva de turno
        validar_turno_horario = timezone.validar_turno_horario(fecha_hora, servicio.minutos_min_reserva)
        if not validar_turno_horario:
            errores_en_servicios.append(exceptions.TurnoReservaAnticipacionInvalidError(minutos_minimos=servicio.minutos_min_reserva))
            continue
        
        # Buscar la disponibilidad válida para este servicio
        disponibilidad_valida = None

        for d in servicio.disponibilidades:
            if d.dia == dia and d.hora_inicio <= hora and d.hora_fin > hora:
                disponibilidad_valida = d
                break

        if not disponibilidad_valida:
            continue # saltamos este servicio si no hay disponibilidad
        
        turnos_actuales_servicio = contar_turnos_superpuestos(db, empresa_id, servicio.id, fecha_hora, servicio.duracion)

        conflicto_usuario = tiene_turno_superpuesto(turnos_actuales_usuario, fecha_hora, servicio.duracion)

        if conflicto_usuario:
            errores_en_servicios.append(exceptions.TurnoUserOverlappingAppointmentError())
            continue
        
        if servicio.profesional_id != 1:

            turnos_actuales_profesional = db.query(models.Turno).filter_by(
                profesional_id=servicio.profesional_id, estado_turno_empresa_id=1 # solo turnos confirmados cuento
            ).all()

            conflicto_profesional = tiene_turno_superpuesto(turnos_actuales_profesional, fecha_hora, servicio.duracion)

            if conflicto_profesional:
                if len(turnos_posibles) == 1:
                    raise exceptions.TurnoProfesionalOverlappingAppointmentError(
                        apellido=servicio.profesional.apellido, nombre=servicio.profesional.nombre
                    )
                errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
                continue # saltamos este servicio si el profesional tiene otro turno superpuesto y no hay disponibilidad
        
        if len(turnos_actuales_servicio) >= disponibilidad_valida.cant_turnos_max:
            errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
            continue
        
        servicios_posibles.append(servicio)
    
    if not servicios_posibles:

        PRIORIDAD_ERRORES = [
            exceptions.TurnoSinDisponibilidadError,
            exceptions.TurnoUserOverlappingAppointmentError,
            exceptions.TurnoReservaAnticipacionInvalidError,
            exceptions.TurnoReservaFueraDeRangoError,
            exceptions.TurnoReservaDisponibilidadNoConfiguradaError,
            exceptions.EmpresaServiceNotFoundError,
        ]

        for clase_error in PRIORIDAD_ERRORES:
            mapear_error_en_reserva_turno(errores_en_servicios, clase_error)

    # Se puede reservar y elegimos uno de los servicios de la lista al azar
    servicio_elegido = random.choice(servicios_posibles)

    try:
        turno = models.Turno(
            usuario_id=usuario_id,
            empresa_id=empresa_id,
            fecha_hora=timezone.to_naive_utc(fecha_hora),
            servicio_id=servicio_elegido.id,
            nombre_de_servicio=servicio_elegido.nombre,
            duracion=servicio_elegido.duracion,
            precio=servicio_elegido.precio,
            aclaracion_de_servicio=servicio_elegido.aclaracion,
            profesional_id=servicio_elegido.profesional_id,
            estado_turno_usuario_id=1, # CONFIRMADO
            estado_turno_empresa_id=1, # CONFIRMADO
            eliminado=None,
            recordatorio_minutos_antes=recordatorio_minutos_antes)            
        db.add(turno)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

def update_turno(db: Session, user: models.Usuario, turno_update: schemas_common.TurnoUpdateIn):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.empresa)).filter_by(id=turno_update.id, usuario_id=user.id).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    get_empresa(db, turno.empresa_id)
    
    nuevo_estado = turno_update.estado_turno
    nuevo_recordatorio = turno_update.recordatorio
    inicio_turno = timezone.ensure_utc(turno.fecha_hora) # convertimos de naive UTC a aware UTC
    email_cancelacion = False

    try:
        if nuevo_estado:
            # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno para luego ponerlo en el turno
            estado_obj = db.query(models.Estado_Turno).filter(
                models.Estado_Turno.estado.ilike(nuevo_estado)).first()

            nuevo_estado_check(db, nuevo_estado, inicio_turno, turno.duracion)

            if turno.estado_turno_usuario_id != 1: # si no es CONFIRMADO el estado
                raise exceptions.TurnoUpdateStateImmutableError()

            turno.estado_turno_usuario_id = estado_obj.id

            if nuevo_estado == 'CANCELADO_POR_USUARIO':
                turno.estado_turno_empresa_id = estado_obj.id
                email_cancelacion = True

        if nuevo_recordatorio:

            turno.recordatorio_minutos_antes = nuevo_recordatorio
        
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    if email_cancelacion:
        try:
            mensajes.send_turno_cancelado_email(
                to_email=turno.empresa.email,
                us_emp_nombre=f"{turno.usuario.apellido}, {turno.usuario.nombre}",
                fecha_hora=inicio_turno,
                servicio=turno.nombre_de_servicio,
                motivo=turno_update.motivo)
        except exceptions.EmailSendFailedError():
            pass

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
def delete_turno(db: Session, usuario_id: int, turno_id: int, lista_estados: list):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario)
    ).filter_by(id=turno_id, usuario_id=usuario_id).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()

    # Esto me va a asegurar que el usuario o empresa tenga que cambiarle el estado a uno de los 
    # posibles para poder mover el turno a la tabla Historial y no que lo mueva sin haber cambiado 
    # el estado previamente y de esta manera, el historial quede con los estados bien puestos
    # (por seguridad si la petición de eliminación llega antes que la de cambio de estado)
    if turno.estado_turno_usuario.estado not in lista_estados:
        raise exceptions.TurnoDeleteStateConflictError()
    
    try:
        # Modificar solo el atributo eliminado del turno si es NULL por 'u' o 's' según quién lo haya eliminado. Si ya es 'u' o 's', 
        # modificar el estado que corresponda de la tabla Historial y luego eliminar turno de la tabla Turno
        if turno.eliminado == None:
            historial = models.Historial(
                usuario_id=turno.usuario_id,
                empresa_id=turno.empresa_id,
                fecha_hora=turno.fecha_hora,
                nombre_de_servicio=turno.nombre_de_servicio,
                duracion=turno.duracion,
                precio=turno.precio,
                aclaracion_de_servicio=turno.aclaracion_de_servicio,
                profesional_id=turno.profesional_id,
                estado_turno_usuario_id=turno.estado_turno_usuario_id,
                estado_turno_empresa_id=None)

            turno.eliminado = 'u' # turno eliminado por el usuario
        
            db.add(historial)
        else:
            # Busco el turno en historial para poder modificarlo
            turno_en_historial = db.query(models.Historial).filter(
                    models.Historial.usuario_id == turno.usuario_id,
                    models.Historial.empresa_id == turno.empresa_id,
                    models.Historial.fecha_hora == turno.fecha_hora,
                    models.Historial.nombre_de_servicio == turno.nombre_de_servicio,
                    models.Historial.profesional_id == turno.profesional_id).first()
            if not turno_en_historial:
                raise exceptions.TurnoHistorialNotFoundError()

            # Significa que el turno ya fue movido por la empresa a la tabla Historial y solo queda 
            # agarrar el estado en estado_turno_usuario_id del turno de la tabla Turno (es un número entero)
            # y ponerlo en el atributo estado_turno_usuario_id del turno de la tabla Historial.
            e = turno.estado_turno_usuario_id
            turno_en_historial.estado_turno_usuario_id = e

            db.delete(turno)

        db.commit()
    except Exception:
        db.rollback()
        raise

def get_estados_turnos(db: Session, usuario_id: int):

    turnos = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario)).filter_by(usuario_id=usuario_id).all()
    
    return turnos

# Devuelve todos los turnos que el usuario ya completó
'Así se pediría, por ejemplo, en la solicitud HTTP: GET /usuarios/5/historial?before=2025-10-10T00:00:00'
def get_historial(db: Session, usuario_id: int, fecha_hora_ultima: datetime, limit=20):
    '''
    Devuelve el historial de turnos de un usuario o empresa con paginación.
    Van ordenados del más reciente al más antiguo (fecha ascendente).
    '''
    query = db.query(models.Historial).filter(models.Historial.usuario_id == usuario_id)

    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Historial
    query = query.options(
        joinedload(models.Historial.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Historial.empresa), # Empresa relacionada
        joinedload(models.Historial.estado_turno_usuario) # Estado del turno del usuario
    )

    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) # garantía defensiva

    query = query.order_by(models.Historial.fecha_hora.desc())
    query = query.filter(models.Historial.fecha_hora < fecha_hora_ultima)

    # historial es una lista de objetos de clase Historial de SQLAlchemy
    historial = query.limit(limit).all()

    # ultimo_cursor es el atributo fecha_hora del último turno en la lista historial (el más antiguo de los devueltos), por lo que su tipo es datetime
    ultimo_cursor = historial[-1].fecha_hora if historial else None 

    return historial, ultimo_cursor

# Devuelve lista de empresas por nombre y/o servicio
def get_empresas(db: Session, query: str, lat: float, lng: float):
    empresas = (
        db.query(models.Empresa)
        .join(models.Servicio)  # Hace que cargue solo las empresas que tienen al menos un servicio asociado
        .filter(
            or_( # or_ busca coincidencias tanto en nombre de empresa como en nombre de rubros.
                models.Empresa.nombre.ilike(f"%{query}%"), 
                models.Empresa.rubro.ilike(f"%{query}%"),
                models.Empresa.rubro2.ilike(f"%{query}%")))
        .options(
            joinedload(models.Empresa.telefonos),
            joinedload(models.Empresa.direccion))
        .distinct().all() # Devuelve lista sin duplicados
    )

    if not empresas:
        return []

    # 2) Lógica de radios crecientes
    radios = [2, 5, 10, 20, 50]  # kilómetros
    resultados = []

    for r in radios:
        for e in empresas:
            if (not e.direccion) or (e.direccion.lat is None) or (e.direccion.lng is None):
                continue

            dist = auxiliares.distancia_km(lat, lng, e.direccion.lat, e.direccion.lng)

            if dist <= r:
                if e not in resultados:
                    resultados.append(e)

    return resultados # resultados es una lista de objetos de clase Empresa de SQLAlchemy

def get_servicios_de_empresa(db: Session, usuario_id: int, empresa_id: int):

    get_empresa(db, empresa_id)

    bloqueo = db.query(models.Empresa_Bloqueo).filter_by(empresa_id=empresa_id, usuario_id=usuario_id).first()
    if bloqueo:
        raise EmpresaUserBlockedError()

    servicios = (
        db.query(models.Servicio)
        .options(
            selectinload(models.Servicio.disponibilidades),
            joinedload(models.Servicio.profesional))
        .filter(models.Servicio.empresa_id == empresa_id)
        .all()
    )

    if not servicios:
        return ([], [])

    # Devuelvo los turnos de la empresa que tiene como confirmados    
    turnos = (
        db.query(models.Turno)
        .filter(
            models.Turno.empresa_id == empresa_id,
            models.Turno.estado_turno_usuario_id == 1,
            models.Turno.estado_turno_empresa_id == 1
        )
        .all()
    )
    
    return servicios, turnos

def add_favorito(db: Session, user_id: int, empresa_id: int):

    empresa = get_empresa(db, empresa_id)

    fav = db.query(models.Favorito).filter(
            models.Favorito.usuario_id == user_id,
            models.Favorito.empresa_id == empresa_id).first()

    if fav:
        raise exceptions.EmpresaAlreadyExistsInFavoritosError()
    
    try:
        db.add(models.Favorito(usuario_id=user_id, empresa_id=empresa_id))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return empresa

def delete_favorito(db: Session, user_id: int, empresa_id: int):

    empresa = get_empresa(db, empresa_id)

    fav = db.query(models.Favorito).filter(
            models.Favorito.usuario_id == user_id,
            models.Favorito.empresa_id == empresa_id).first()

    if not fav:
        raise exceptions.EmpresaDoesNotExistInFavoritosError()
    
    try:
        db.delete(fav)
        db.commit()
    except Exception:
        db.rollback()
        raise

def agregar_calificacion(db: Session, empresa_id: int, valor: int):

    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise exceptions.EmpresaNotFoundError()

    try:
        # Guardar calificación
        calif = models.Calificacion(empresa_id=empresa_id, valor=valor)
        db.add(calif)
        db.flush()

        # Recalcular promedio
        califs = db.query(models.Calificacion).filter(models.Calificacion.empresa_id == empresa_id).all()
        promedio = round(sum(c.valor for c in califs) / len(califs), 2)
        empresa.calificacion = promedio

        db.commit()
    except Exception:
        db.rollback()
        raise