import random
from datetime import date, time, datetime, timedelta

from jose import jwt
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, joinedload, selectinload

from crud.common import get_empresa, get_sucursal, nuevo_estado_check, contar_turnos_superpuestos_servicio, tiene_turno_superpuesto
from core import models, constantes, exceptions, autenticacion, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario

# Crear usuario
def create_usuario(db: Session, user: schemas_usuario.UserCreate):

    # Verificar si el email ya existe
    usuario_existe = db.query(models.Usuario).filter_by(email=user.email).first()
    if usuario_existe and usuario_existe.email_verificado:
        raise exceptions.UserAlreadyExistsError()
    if usuario_existe and not usuario_existe.email_verificado:
        return usuario_existe

    password = user.password.get_secret_value()

    try:
        # Crear el objeto de usuario
        db_user = models.Usuario(
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,
            email_verificado=False,
            hashed_password=autenticacion.get_password_hash(password),
            recordatorio_minutos_antes=user.recordatorio,
            fecha_hora_alta=None,
        )

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
            dir_user = models.Dir_Usuario(usuario_id=db_user.id, direccion_id=db_dir.id)
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

    query = db.query(models.Turno).filter(
        models.Turno.usuario_id == usuario_id,
        models.Turno.eliminado_por_usuario == False,
    )
    
    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Turno
    query = query.options(
        joinedload(models.Turno.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.empresa),
        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.direccion),
        joinedload(models.Turno.estado_turno_usuario), # Estado del turno del usuario
        joinedload(models.Turno.recordatorio),
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
                    db.add(models.Dir_Usuario(usuario_id=user.id, direccion_id=db_dir.id))

            # Eliminar direcciones eliminadas
            for old_id in list(current_dirs.keys()):
                if old_id not in new_dir_ids:
                    dir_usuario = db.query(models.Dir_Usuario).filter_by(usuario_id=user.id, direccion_id=old_id).first()
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
            selectinload(models.Usuario.telefonos),
            joinedload(models.Usuario.direcciones))
        .filter(models.Usuario.id == user.id).first()
    )
    return user # user es un objeto de clase Usuario de SQLAlchemy

def get_turno(db: Session, turno_id: int):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.empresa),
        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.direccion),
        joinedload(models.Turno.estado_turno_usuario),
        joinedload(models.Turno.recordatorio),
    ).filter(
        models.Turno.id == turno_id.
        models.Turno.eliminado_por_usuario == False,
    ).first()
    
    return turno

def mapear_error_en_reserva_turno(errores_en_servicios, clase_error):
    '''
    Lo malo que tiene esta función es que si hay algo de metada en las excepciones y hay
    dos o más excepciones de igual clase pero distinta metada, devolverá la primera
    que encuentre, haciendo que especifique la metadata de uno solo de los servicios. Es algo muy menor pero vale aclararlo.
    '''
    for error in errores_en_servicios:
        if isinstance(error, clase_error):
            raise error

def reservar_turno(db: Session, usuario: models.Usuario, reserva: schemas_usuario.ReservaTurnoOpcionesUserIn):

    usuario_id = usuario.id
    recordatorio_minutos_antes = usuario.recordatorio_minutos_antes

    # Traer sucursal y servicio
    turnos_posibles = reserva.opciones # lista de ReservaTurnoUserIn

    sucursal_id = turnos_posibles[0].sucursal_id # tomamos el primero, total los sucursal_id son todos iguales

    fecha_hora = turnos_posibles[0].fecha_hora # tomamos el primero, total los fecha_hora son todos iguales

    sucursal = get_sucursal(db, sucursal_id)

    nombre_completo_sucursal = auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre)

    if not sucursal.reserva_publica_habilitada:
        raise exceptions.SucursalReservaPublicaInhabilitadaError(nombre=nombre_completo_sucursal)

    bloqueo = (
        db.query(models.BloqueoSucursal)
        .join(models.Cliente)
        .filter(
            models.BloqueoSucursal.sucursal_id == sucursal_id,
            models.Cliente.email == usuario.email,
        )
        .first()
    )

    if bloqueo:
        raise exceptions.UserBlockedBySucursalError(nombre=nombre_completo_sucursal)

    dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

    turnos_actuales_usuario = db.query(models.Turno).filter_by(
        usuario_id=usuario_id,
        eliminado_por_usuario=False,
        estado_turno_usuario_id=1, # solo turnos confirmados cuento
    ).all()

    errores_en_servicios = []
    servicios_posibles = [] # lista de tuplas de interos como primer elemento y objetos models.Servicio como segundo

    for turno_posible in turnos_posibles:

        servicio = (
            db.query(models.Servicio)
            .filter(
                models.Servicio.id == turno_posible.servicio_id,
                models.Servicio.sucursal_id == turno_posible.sucursal_id,
            )
            .first()
        )

        if not servicio:
            errores_en_servicios.append(exceptions.SucursalServiceNotFoundError())
            continue

        servicio = (
            db.query(models.Servicio)
            .join(models.Disponibilidad)
            .options(
                joinedload(models.Servicio.profesional),
                selectinload(models.Servicio.disponibilidades),
            )
            .filter(
                models.Servicio.id == turno_posible.servicio_id,
                models.Servicio.sucursal_id == turno_posible.sucursal_id,
                models.Disponibilidad.dia == dia,
                models.Disponibilidad.hora_inicio <= hora,
                models.Disponibilidad.hora_fin >= hora,
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

            if d.dia == dia and d.hora_inicio <= hora and d.hora_fin >= hora:

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

                if diferencia_minutos % d.intervalo == 0:
                    disponibilidad_valida = d
                    break

        if not disponibilidad_valida:
            errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
            continue # saltamos este servicio si no hay disponibilidad

        conflicto_usuario = tiene_turno_superpuesto(turnos_actuales_usuario, fecha_hora, servicio.duracion)

        if conflicto_usuario:
            errores_en_servicios.append(exceptions.TurnoUserOverlappingAppointmentError())
            continue
        
        if servicio.profesional_id is not None:

            turnos_actuales_profesional = db.query(models.Turno).filter_by(
                profesional_id=servicio.profesional_id,
                estado_turno_sucursal_id=1, # solo turnos confirmados cuento
            ).all()

            conflicto_profesional = tiene_turno_superpuesto(turnos_actuales_profesional, fecha_hora, servicio.duracion)

            if conflicto_profesional:
                if len(turnos_posibles) == 1:
                    raise exceptions.TurnoProfesionalOverlappingAppointmentError(
                        apellido=servicio.profesional.apellido, nombre=servicio.profesional.nombre
                    )
                errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
                continue # saltamos este servicio si el profesional tiene otro turno superpuesto y no hay disponibilidad
        
        turnos_actuales_servicio = contar_turnos_superpuestos_servicio(db, sucursal_id, servicio.id, fecha_hora, servicio.duracion)
        
        if len(turnos_actuales_servicio) >= disponibilidad_valida.cant_turnos_max:
            errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
            continue

        servicios_posibles.append((disponibilidad_valida, servicio))

    recordatorio_fecha_hora = None
    if recordatorio_minutos_antes is not None:
        recordatorio_fecha_hora = fecha_hora - timedelta(minutes=recordatorio_minutos_antes)
    
    es_cliente = db.query(models.Cliente).filter_by(
        sucursal_id=sucursal_id,
        email=usuario.email,
    ).first()

    telefonos = usuario.telefonos

    try:
        indices_disponibilidades = []
        for tupla in servicios_posibles:
            indices_disponibilidades.append(tupla[0].id)
        # ordenamos la lista en orden ascendente para que no se generen ciclos de bloqueo (ninguna transacción va a pasar
        # de bloquear un registro de la tabla Disponibilidad de un id superior a uno de id inferior que ya ha
        # bloqueado en la misma transacción)
        indices_disponibilidades.sort()

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.id.in_(indices_disponibilidades))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        disponibilidades_bloqueadas = {d.id: d for d in disponibilidades}

        while len(servicios_posibles) > 0:
            # Se puede reservar y elegimos uno de los servicios de la lista al azar
            indice = random.randrange(len(servicios_posibles))
            tupla_elegida = servicios_posibles[indice]

            disponibilidad_valida = disponibilidades_bloqueadas[tupla_elegida[0].id] # renuevo las disponibilidades (que son las mismas)
            servicio_elegido = tupla_elegida[1]

            turnos_actuales_servicio = contar_turnos_superpuestos_servicio(db, sucursal_id,
                servicio_elegido.id, fecha_hora, servicio_elegido.duracion)

            if len(turnos_actuales_servicio) >= disponibilidad_valida.cant_turnos_max:
                servicios_posibles.pop(indice)
                errores_en_servicios.append(exceptions.TurnoSinDisponibilidadError())
                continue
            else:
                break
        
        if not servicios_posibles:

            PRIORIDAD_ERRORES = [
                exceptions.TurnoSinDisponibilidadError,
                exceptions.TurnoUserOverlappingAppointmentError,
                exceptions.TurnoReservaAnticipacionInvalidError,
                exceptions.TurnoReservaFueraDeRangoError,
                exceptions.TurnoReservaDisponibilidadNoConfiguradaError,
                exceptions.SucursalServiceNotFoundError,
            ]

            for clase_error in PRIORIDAD_ERRORES:
                mapear_error_en_reserva_turno(errores_en_servicios, clase_error)

        if es_cliente:
            if not es_cliente.activo:
                es_cliente.activo = True
        else:
            # Crear cliente
            cliente = models.Cliente(
                sucursal_id=sucursal_id,
                dni=usuario.dni,
                apellido=usuario.apellido,
                nombre=usuario.nombre,
                email=usuario.email,
                telefono=telefonos[0].numero if len(telefonos) >= 1 else None,
                telefono2=telefonos[1].numero if len(telefonos) >= 2 else None,
                observacion=None,
                fecha_hora_alta=timezone.to_naive_utc(timezone.now_utc()),
                activo=True,
            )
            db.add(cliente)

        turno = models.Turno(
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
            fecha_hora=timezone.to_naive_utc(fecha_hora),
            servicio_id=servicio_elegido.id,
            nombre_de_servicio=servicio_elegido.nombre,
            duracion=servicio_elegido.duracion,
            precio=servicio_elegido.precio,
            aclaracion_de_servicio=servicio_elegido.aclaracion,
            profesional_id=servicio_elegido.profesional_id,
            estado_turno_usuario_id=1, # CONFIRMADO
            estado_turno_sucursal_id=1, # CONFIRMADO
            eliminado_por_usuario=False,
            eliminado_por_sucursal=False,
            recordatorio_fecha_hora=timezone.to_naive_utc(recordatorio_fecha_hora) if recordatorio_fecha_hora else None,
            recordatorio_enviado=False,
        )            
        db.add(turno)

        db.commit()
    except Exception:
        db.rollback()
        raise

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

def update_estado_turno(db: Session, usuario: models.Usuario, turno_id: int, turno_update: schemas_usuario.TurnoUpdateIn):

    turno = db.query(models.Turno).filter_by(
        id=turno_id,
        usuario_id=usuario.id, # chequeo que el mismo usuario del turno sea el que hace la request
        eliminado_por_usuario=False, # chequeo que no esté pasado a historial
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    sucursal = get_sucursal(db, turno.sucursal_id, error_if_not_active=False)
    
    nuevo_estado = turno_update.estado_turno
    inicio_turno = timezone.ensure_utc(turno.fecha_hora) # convertimos de naive UTC a aware UTC
    email_cancelacion = False

    try:
        # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno para luego ponerlo en el turno
        estado_obj = db.query(models.Estado_Turno).filter(
            models.Estado_Turno.estado.ilike(nuevo_estado)).first()
        
        if not estado_obj:
            raise ValueError("Error al buscar el ID del estado del turno en la tabla estado_turno de la base de datos")

        nuevo_estado_check(db, nuevo_estado, inicio_turno, turno.duracion)

        if turno.estado_turno_usuario_id != 1: # si no es CONFIRMADO el estado
            raise exceptions.TurnoUpdateStateImmutableError()

        turno.estado_turno_usuario_id = estado_obj.id

        if nuevo_estado == 'CANCELADO_POR_USUARIO':
            turno.estado_turno_sucursal_id = estado_obj.id
            email_cancelacion = True
        
        if nuevo_estado == 'CUMPLIDO' and turno_update.calificacion:
            # Guardar calificación
            calif = models.Calificacion(turno_id=turno_id, valor=turno_update.calificacion)
            db.add(calif)
            db.flush()

            # Recalcular promedio desde turnos de esa sucursal
            promedio = (
                db.query(func.avg(models.Calificacion.valor))
                .join(models.Turno)
                .filter(models.Turno.sucursal_id == turno.sucursal_id)
                .scalar()
            )

            if promedio is not None:
                promedio = round(promedio, 2)

            sucursal.calificacion = promedio
        
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    if email_cancelacion:
        try:
            mensajes.send_turno_cancelado_email(
                to_email=sucursal.empresa.email,
                us_emp_nombre=f"{usuario.apellido}, {usuario.nombre}",
                fecha_hora=inicio_turno,
                servicio=turno.nombre_de_servicio,
                motivo=turno_update.observacion)
        except exceptions.EmailSendFailedError:
            pass

        try:
            if sucursal.email:
                mensajes.send_turno_cancelado_email(
                    to_email=sucursal.email,
                    us_emp_nombre=f"{usuario.apellido}, {usuario.nombre}",
                    fecha_hora=inicio_turno,
                    servicio=turno.nombre_de_servicio,
                    motivo=turno_update.observacion)
        except exceptions.EmailSendFailedError:
            pass

    # Cargar relaciones importantes antes de devolver
    turno = get_turno(db, turno_id)

    return turno

def update_recordatorio_turno(db: Session, usuario_id: int, turno_id: int, nuevo_recordatorio: int | None):

    turno = db.query(models.Turno).filter_by(
        id=turno_id,
        usuario_id=usuario_id, # chequeo que el mismo usuario del turno sea el que hace la request
        eliminado_por_usuario=False, # chequeo que no esté pasado a historial
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    if nuevo_recordatorio is not None:
        recordatorio_fecha_hora = turno.fecha_hora - timedelta(minutes=nuevo_recordatorio)
    else:
        recordatorio_fecha_hora = None

    try:
        turno.recordatorio_fecha_hora = recordatorio_fecha_hora       
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Cargar relaciones importantes antes de devolver
    turno = get_turno(db, turno_id)

    return turno

# Pasa un turno a historial
def delete_turno(db: Session, usuario_id: int, turno_id: int, lista_estados: list):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario),
    ).filter_by(
        id=turno_id,
        usuario_id=usuario_id,
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()

    if turno.eliminado_por_usuario == True:
        return

    # Esto me va a asegurar que el usuario o sucursal tenga que cambiarle el estado a uno de los 
    # posibles para poder eliminar el turno y no que lo elimine sin haber cambiado 
    # el estado previamente y de esta manera, el historial quede con los estados bien puestos
    # (por seguridad si la petición de eliminación llega antes que la de cambio de estado)
    if turno.estado_turno_usuario.estado not in lista_estados:
        raise exceptions.TurnoDeleteStateConflictError()
    
    try:
        turno.eliminado_por_usuario = True
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_estados_turnos(db: Session, usuario_id: int):

    turnos = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario),
    ).filter_by(
        usuario_id=usuario_id,
        eliminado_por_usuario=False,
    ).all()
    
    return turnos

# Devuelve todos los turnos que el usuario ya completó
'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /usuarios/5/turnos/historial?fecha_hora_ultima=2025-10-10T12:00:00Z&id_ultimo=1234&limit=50
'''
def get_historial(db: Session, usuario_id: int,
    fecha_hora_ultima: datetime | None = None, id_ultimo: int | None = None, limit: int = 50):
    '''
    Devuelve el historial de turnos de un usuario con paginación.
    Van ordenados del más reciente al más antiguo (fecha descendente).

    Parámetros:
        fecha_hora_ultima: datetime del último turno recibido (para la siguiente página).
        id_ultimo: id del último turno recibido (para la siguiente página).
        limit: cantidad máxima de turnos a devolver (máx 100).
    
    Proceso:
        Primera solicitud: front no envía cursor → back devuelve primeros N registros + cursor del último.
        Siguientes solicitudes: front envía cursor → back devuelve los siguientes N registros + cursor actualizado.
        Última página: back devuelve lista vacía y cursor None → front deja de pedir más.
    '''
    query = db.query(models.Turno).options(
        joinedload(models.Turno.profesional), # usuario relacionado (como profesional)
        joinedload(models.Turno.sucursal).joinedload(models.Sucursal.empresa), # sucursal y empresa relacionadas
        joinedload(models.Turno.estado_turno_usuario) # estado del turno del usuario
    ).filter(
        models.Turno.usuario_id == usuario_id,
        models.Turno.eliminado_por_usuario == True,
    )

    # Aplicar paginación por cursor compuesto si se envió fecha_hora_ultima y id_ultimo
    if fecha_hora_ultima and id_ultimo:
        fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) # garantía defensiva
        query = query.filter(
            or_(
                models.Turno.fecha_hora < fecha_hora_ultima,
                and_(
                    models.Turno.fecha_hora == fecha_hora_ultima,
                    models.Turno.id < id_ultimo,
                )
            )
        )

    query = query.order_by(models.Turno.fecha_hora.desc(), models.Turno.id.desc())

    limit = min(limit, 100) # no más de 100 por consulta

    # historial es una lista de objetos de clase Turno de SQLAlchemy
    historial = query.limit(limit).all()

    # Último cursor para la siguiente página.
    # ultimo_cursor_fecha_hora es el atributo fecha_hora del último turno en la lista historial
    # (el más antiguo de los devueltos), por lo que su tipo es datetime.
    if historial:
        ultimo_cursor_fecha_hora = historial[-1].fecha_hora
        ultimo_cursor_id = historial[-1].id
    else:
        ultimo_cursor_fecha_hora = None
        ultimo_cursor_id = None

    return historial, (ultimo_cursor_fecha_hora, ultimo_cursor_id)

# Devuelve lista de sucursales por nombre y/o servicio
def get_sucursales(db: Session, search: str, lat: float, lng: float):
    sucursales = (
        db.query(models.Sucursal)
        .join(models.Empresa) # para poder filtrar por nombre de empresa
        .join(models.Servicio) # hace que cargue solo las sucursales que tienen al menos un servicio asociado
        .filter(
            models.Sucursal.activa == True, # solo activas
            models.Sucursal.reserva_publica_habilitada == True, # solo las que permiten a los usuarios reservar
            or_(
                models.Sucursal.nombre.ilike(f"%{search}%"),
                models.Empresa.nombre.ilike(f"%{search}%"),
                models.Empresa.rubro.ilike(f"%{search}%"),
                models.Empresa.rubro2.ilike(f"%{search}%"),
            )
        )
        .options(
            joinedload(models.Sucursal.empresa),
            selectinload(models.Sucursal.telefonos),
            joinedload(models.Sucursal.direccion),
        )
        .distinct().all() # devuelve lista sin duplicados
    )

    if not sucursales:
        return []

    # 2) Lógica de radios crecientes
    radios = [2, 5, 10, 20, 50] # kilómetros
    resultados = []

    for r in radios:
        for s in sucursales:
            if (not s.direccion) or (s.direccion.lat is None) or (s.direccion.lng is None):
                continue

            dist = auxiliares.distancia_km(lat, lng, s.direccion.lat, s.direccion.lng)

            if dist <= r:
                if s not in resultados:
                    resultados.append(s)

    return resultados # resultados es una lista de objetos de clase Sucursal de SQLAlchemy

def get_servicios_de_sucursal(db: Session, usuario_email: str, sucursal_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    nombre_sucursal = auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre)

    if not sucursal.reserva_publica_habilitada:
        raise exceptions.SucursalReservaPublicaInhabilitadaError(nombre=nombre_sucursal)
    
    bloqueo = (
        db.query(models.BloqueoSucursal)
        .join(models.Cliente)
        .filter(
            models.BloqueoSucursal.sucursal_id == sucursal_id,
            models.Cliente.email == usuario_email,
        )
        .first()
    )

    if bloqueo:
        raise exceptions.UserBlockedBySucursalError(nombre=nombre_completo_sucursal)

    servicios = (
        db.query(models.Servicio)
        .options(
            selectinload(models.Servicio.disponibilidades),
            joinedload(models.Servicio.profesional),
        )
        .filter(models.Servicio.sucursal_id == sucursal_id)
        .all()
    )

    if not servicios:
        return ([], [])

    # Devuelvo los turnos de la sucursal que tiene como confirmados    
    turnos = (
        db.query(models.Turno)
        .filter(
            models.Turno.sucursal_id == sucursal_id,
            models.Turno.eliminado_por_sucursal == False,
            models.Turno.estado_turno_usuario_id == 1,
            models.Turno.estado_turno_sucursal_id == 1,
        )
        .all()
    )
    
    return servicios, turnos

def add_favorito(db: Session, usuario_id: int, sucursal_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    fav = db.query(models.Favorito).filter(
        models.Favorito.usuario_id == usuario_id,
        models.Favorito.sucursal_id == sucursal_id,
    ).first()

    if fav:
        raise exceptions.SucursalAlreadyExistsInFavoritosError()
    
    try:
        db.add(models.Favorito(usuario_id=usuario_id, sucursal_id=sucursal_id))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return sucursal

def delete_favorito(db: Session, usuario_id: int, sucursal_id: int):

    fav = db.query(models.Favorito).filter(
        models.Favorito.usuario_id == usuario_id,
        models.Favorito.sucursal_id == sucursal_id,
    ).first()

    if not fav:
        raise exceptions.SucursalDoesNotExistInFavoritosError()
    
    try:
        db.delete(fav)
        db.commit()
    except Exception:
        db.rollback()
        raise