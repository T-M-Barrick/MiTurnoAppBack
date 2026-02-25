from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import UploadFile
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload, selectinload
import cloudinary.uploader

from crud.common import (get_empresa, get_sucursal, verificar_rol_en_empresa, verificar_rol_en_sucursal,
verificar_rol_en_empresa_o_sucursal, nuevo_estado_check, contar_turnos_superpuestos_servicio, tiene_turno_superpuesto)
from core import models, constantes, exceptions, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal

def create(db: Session, usuario_id: int, nueva_sucursal: schemas_sucursal.SucursalCreate):

    empresa = get_empresa(db, nueva_sucursal.empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa.id)

    if current_user_rol != 'propietario':
        raise exceptions.SucursalCreatedByGerenteEmpresaError()

    sucursal_existe = db.query(models.Sucursal).filter_by(
        empresa_id=empresa.id,
        nombre=nueva_sucursal.nombre,
    ).first()
    
    if sucursal_existe and sucursal_existe.nombre is not None:
        raise exceptions.SucursalAlreadyExistsWithNameError()
    if sucursal_existe and sucursal_existe.nombre is None:
        raise exceptions.SucursalAlreadyExistsWithoutNameError()

    try:
        # Crear el objeto de sucursal
        db_sucursal = models.Sucursal(
            empresa_id=empresa.id,
            nombre=nueva_sucursal.nombre,
            email=None,
            email_verificado=None,
            reserva_publica_habilitada=nueva_sucursal.reserva_publica_habilitada,
            calificacion=None,
            activa=True,
        )

        db.add(db_sucursal)
        db.flush()

        # Agregar teléfonos
        for t in nueva_sucursal.telefonos:
            db_tel = models.Telefono(numero=t.numero, sucursal_id=db_sucursal.id)
            db.add(db_tel)
        
            # Agregar dirección
        db_dir = models.Direccion(
            sucursal_id=db_sucursal.id,
            calle=nueva_sucursal.direccion.calle,
            altura=nueva_sucursal.direccion.altura,
            localidad=nueva_sucursal.direccion.localidad,
            departamento=nueva_sucursal.direccion.departamento,
            provincia=nueva_sucursal.direccion.provincia,
            pais=nueva_sucursal.direccion.pais,
            lat=nueva_sucursal.direccion.lat,
            lng=nueva_sucursal.direccion.lng,
            aclaracion=nueva_sucursal.direccion.aclaracion,
        )

        db.add(db_dir)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return db_sucursal

def acceder(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id)
    current_user_rol = verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    return sucursal, current_user_rol

def update(db: Session, sucursal_id: int, usuario_id: int, sucursal_update: schemas_sucursal.SucursalUpdateIn):

    db_suc = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, db_suc.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = sucursal_update.dict(exclude_unset=True)

    # Chequeo si ya existe otra sucursal en la empresa con el mismo nombre
    nombre_nuevo = update_data.get("nombre", db_suc.nombre) # Si no vino, uso el nombre que ya estaba

    sucursal_existe = db.query(models.Sucursal).filter(
        models.Sucursal.id != sucursal_id,
        models.Sucursal.empresa_id == db_suc.empresa.id,
        models.Sucursal.nombre == nombre_nuevo,
    ).first()

    if sucursal_existe and sucursal_existe.nombre is not None:
        raise exceptions.SucursalAlreadyExistsWithNameError()
    if sucursal_existe and sucursal_existe.nombre is None:
        raise exceptions.SucursalAlreadyExistsWithoutNameError()
    
    try:
        # ----------------------------
        # 1️⃣ Actualizar campos simples
        # ----------------------------
        for attr, value in update_data.items():
            if attr not in ["telefonos", "direccion"]:
                setattr(db_suc, attr, value)

        # ----------------------------
        # 2️⃣ Actualizar TELÉFONOS
        # ----------------------------
        if sucursal_update.telefonos is not None:
            current_phones = {t.id: t for t in db_suc.telefonos}
            new_ids = set()

            for tel in sucursal_update.telefonos: # tel es un objeto de la clase schema TelefonoConID

                if tel.id and tel.id in current_phones:
                    # Actualizar teléfono existente
                    db_tel = current_phones[tel.id]
                    db_tel.numero = tel.numero
                    new_ids.add(tel.id)
                else:
                    # Crear nuevo teléfono
                    new_tel = models.Telefono(numero=tel.numero, sucursal_id=sucursal_id)
                    db.add(new_tel)

            # Eliminar teléfonos que ya no están en la lista
            for old_id in list(current_phones.keys()):
                if old_id not in new_ids:
                    db.delete(current_phones[old_id])

        # ----------------------------
        # 3️⃣ Actualizar DIRECCIÓN
        # ----------------------------
        if sucursal_update.direccion is not None:
            d = sucursal_update.direccion
            if db_suc.direccion:
                db_dir = db_suc.direccion
                if d.id and db_dir.id == d.id:
                    db_dir.calle = d.calle
                    db_dir.altura = d.altura
                    db_dir.localidad = d.localidad
                    db_dir.departamento = d.departamento
                    db_dir.provincia = d.provincia
                    db_dir.pais = d.pais
                    db_dir.lat = d.lat
                    db_dir.lng = d.lng
                    db_dir.aclaracion = d.aclaracion
                else:
                    # Reemplazar por nueva dirección
                    db.delete(db_suc.direccion)
                    new_dir = models.Direccion(
                        sucursal_id=sucursal_id,
                        calle=d.calle,
                        altura=d.altura,
                        localidad=d.localidad,
                        departamento=d.departamento,
                        provincia=d.provincia,
                        pais=d.pais,
                        lat=d.lat,
                        lng=d.lng,
                        aclaracion=d.aclaracion)
                    db.add(new_dir)
            else:
                # Crear nueva dirección
                new_dir = models.Direccion(
                    sucursal_id=sucursal_id,
                    calle=d.calle,
                    altura=d.altura,
                    localidad=d.localidad,
                    departamento=d.departamento,
                    provincia=d.provincia,
                    pais=d.pais,
                    lat=d.lat,
                    lng=d.lng,
                    aclaracion=d.aclaracion,
                )
                db.add(new_dir)

        db.commit()

    except Exception:
        db.rollback()
        raise
    
    sucursal = get_sucursal(db, sucursal_id)

    return sucursal, current_user_rol

def deactivate(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    # verificar permisos
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, sucursal.empresa.id)

    if current_user_rol != 'propietario':
        raise exceptions.SucursalDeactivateForbiddenError()
    
    turno_confirmado = db.query(models.Turno).filter(
        models.Turno.sucursal_id == sucursal_id,
        models.Turno.eliminado_por_sucursal == False,
        models.Turno.estado_turno_sucursal_id == 1,
    ).first()

    if turno_confirmado:
        raise exceptions.SucursalDeactivateConTurnosConfirmadosError()

    try:
        sucursal.activa = False
        db.commit()
    except Exception:
        db.rollback()
        raise

def reactivate(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    # verificar permisos
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, sucursal.empresa.id)

    if current_user_rol != 'propietario':
        raise exceptions.SucursalActivateForbiddenError()

    try:
        sucursal.activa = True
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_clientes(db: Session, sucursal_id: int,
    usuario_id: int, search: str | None = None, activo: bool | None = None, id_ultimo: int | None = None, limit: int = 50):

    db_suc = get_sucursal(db, sucursal_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, db_suc.empresa.id, sucursal_id)

    query = db.query(models.Cliente).filter(models.Cliente.sucursal_id == sucursal_id)

    # Filtro por activo (IMPORTANTE usar is not None)
    if activo is not None:
        query = query.filter(models.Cliente.activo == activo)

    # Cursor de paginación
    if id_ultimo is not None:
        query = query.filter(models.Cliente.id < id_ultimo)

    # Búsqueda global
    if search:
        palabra = f"%{search}%"
        query = query.filter(
            or_(
                models.Cliente.dni.ilike(palabra),
                models.Cliente.apellido.ilike(palabra),
                models.Cliente.nombre.ilike(palabra),
                models.Cliente.email.ilike(palabra),
                models.Cliente.telefono.ilike(palabra),
                models.Cliente.telefono2.ilike(palabra),
            )
        )

    # Orden descendente para que el más reciente (id más grande) sea el primero de la lista
    clientes = query.order_by(models.Cliente.id.desc()).limit(limit).all()

    # Nuevo cursor
    ultimo_cursor_id = clientes[-1].id if clientes else None

    return clientes, ultimo_cursor_id

def create_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_nuevo: schemas_sucursal.ClienteCreate):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    # Chequeo si ya existe un cliente igual en la sucursal con el mismo email
    cliente_existe = db.query(models.Cliente).filter_by(
        sucursal_id=sucursal_id,
        email=cliente_nuevo.email,
    ).first()

    if cliente_existe:
        raise exceptions.ClienteAlreadyExistsError()

    try:
        # Crear cliente
        cliente = models.Cliente(
            sucursal_id=sucursal_id,
            dni=cliente_nuevo.dni,
            apellido=cliente_nuevo.apellido,
            nombre=cliente_nuevo.nombre,
            email=cliente_nuevo.email,
            telefono=cliente_nuevo.telefono,
            telefono2=cliente_nuevo.telefono2,
            observacion=cliente_nuevo.observacion,
            fecha_hora_alta=timezone.to_naive_utc(timezone.now_utc()),
            activo=True,
        )

        db.add(cliente)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return cliente

def update_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_id: int, cliente_update: schemas_sucursal.ClienteUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()
    
    # Convertir a dict solo con campos enviados
    update_data = cliente_update.dict(exclude_unset=True)

    # Chequeo si ya existe otro cliente en la sucursal con el mismo email
    email_nuevo = update_data.get("email", cliente.email) # Si no vino, uso el email que ya estaba

    cliente_existe = db.query(models.Cliente).filter(
        models.Cliente.id != cliente_id,
        models.Cliente.sucursal_id == sucursal_id,
        models.Cliente.email == email_nuevo,
    ).first()

    if cliente_existe:
        raise exceptions.ClienteAlreadyExistsError()
    
    try:
        for attr, value in update_data.items():
                setattr(cliente, attr, value)

        db.commit()
        db.refresh(cliente)
    except Exception:
        db.rollback()
        raise

    return cliente

def deactivate_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()
    
    turno_confirmado = db.query(models.Turno).filter(
        models.Turno.sucursal_id == sucursal_id,
        models.Turno.eliminado_por_sucursal == False,
        models.Turno.estado_turno_sucursal_id == 1,
        models.Turno.cliente_id == cliente_id,
    ).first()

    if turno_confirmado:
        raise exceptions.ClienteDeactivateConTurnosConfirmadosError()

    try:
        cliente.activo = False
        db.commit()
    except Exception:
        db.rollback()
        raise

def reactivate_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()

    try:
        cliente.activo = True
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_turnos(db: Session, sucursal_id: int, usuario_id: int):
    '''
    Devuelve todos los turnos de una sucursal que aparecen en la tabla turno: los futuros y los pasados que la sucursal no eliminó.
    Van ordenados del más antiguo al más lejano (fecha descendente).
    '''
    db_suc = get_sucursal(db, sucursal_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, db_suc.empresa.id, sucursal_id)

    query = db.query(models.Turno).filter(
        models.Turno.sucursal_id == sucursal_id,
        models.Turno.eliminado_por_sucursal == False,
    )

    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Turno
    query = query.options(
        joinedload(models.Turno.usuario), # Usuario relacionado
        joinedload(models.Turno.cliente), # Cliente relacionado
        joinedload(models.Turno.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Turno.estado_turno_sucursal) # Estado del turno de la sucursal
    )
    
    # Los que tienen fecha más antigua aparecerán más arriba que los de fecha más futura en el tiempo
    turnos = query.order_by(models.Turno.fecha_hora.asc()).all()

    return turnos # turnos es una lista de objetos de clase Turno de SQLAlchemy

def get_turno(db: Session, turno_id: int):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.cliente),
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.estado_turno_sucursal),
    ).filter(
        models.Turno.id == turno_id,
        models.Turno.eliminado_por_sucursal == False,
    ).first()
    
    return turno

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

def reservar_turno(db: Session, sucursal_id: int, usuario_miembro_id: int, reserva: schemas_usuario.ReservaTurnoSucursalIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_miembro_id, sucursal.empresa.id, sucursal_id)

    cliente_id = reserva.cliente_id
    servicio_id = reserva.servicio_id
    fecha_hora = reserva.fecha_hora

    dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()

    bloqueo = db.query(models.BloqueoSucursal).filter_by(sucursal_id=sucursal_id, cliente_id=cliente_id).first()
    if bloqueo:
        raise exceptions.SucursalClienteBlockedError()
    
    usuario_cliente = db.query(models.Usuario).filter_by(email=cliente.email).first()

    turnos_actuales_usuario_cliente = []

    if usuario_cliente:
        turnos_actuales_usuario_cliente = db.query(models.Turno).filter_by(
            usuario_id=usuario_cliente.id,
            eliminado_por_usuario=False,
            estado_turno_usuario_id=1, # solo turnos confirmados cuento
        ).all()

    servicio = (
        db.query(models.Servicio)
        .filter(
            models.Servicio.id == servicio_id,
            models.Servicio.sucursal_id == sucursal_id,
        )
        .first()
    )

    if not servicio:
        raise exceptions.SucursalServiceNotFoundError()

    servicio = (
        db.query(models.Servicio)
        .join(models.Disponibilidad)
        .options(
            joinedload(models.Servicio.profesional),
            selectinload(models.Servicio.disponibilidades),
        )
        .filter(
            models.Servicio.id == servicio_id,
            models.Servicio.sucursal_id == sucursal_id,
            models.Disponibilidad.dia == dia,
            models.Disponibilidad.hora_inicio <= hora,
            models.Disponibilidad.hora_fin >= hora,
        )
        .first()
    )

    if not servicio:
        raise exceptions.TurnoReservaDisponibilidadNoConfiguradaError()
    
    # Validar límite máximo de días
    if servicio.dias_max_reserva is not None:
        validar_turno_dias_max = timezone.validar_turno_dias_max(fecha_hora, servicio.dias_max_reserva)
        if not validar_turno_dias_max:
            raise exceptions.TurnoReservaFueraDeRangoError(dias_max=servicio.dias_max_reserva)
    
    # Buscar la disponibilidad válida para este servicio
    disponibilidad_valida = None

    for d in servicio.disponibilidades:

        if disponibilidad_cubre_turno(d, fecha_hora):
            disponibilidad_valida = d
            break

    if not disponibilidad_valida:
        raise exceptions.TurnoSinDisponibilidadError()
        # seguir aca la modificacion de esta funcion

    conflicto_usuario = tiene_turno_superpuesto(turnos_actuales_usuario_cliente, fecha_hora, servicio.duracion)

    if conflicto_usuario:
        raise exceptions.TurnoUserOverlappingAppointmentError()
    
    if servicio.profesional_id is not None:

        turnos_actuales_profesional = db.query(models.Turno).filter_by(
            profesional_id=servicio.profesional_id,
            estado_turno_sucursal_id=1, # solo turnos confirmados cuento
        ).all()

        conflicto_profesional = tiene_turno_superpuesto(turnos_actuales_profesional, fecha_hora, servicio.duracion)

        if conflicto_profesional:
            raise exceptions.TurnoProfesionalOverlappingAppointmentError(
                apellido=servicio.profesional.apellido, nombre=servicio.profesional.nombre
            )
    
    recordatorio_fecha_hora = None

    if usuario_cliente:
        if usuario_cliente.recordatorio_minutos_antes is not None:
            recordatorio_fecha_hora = fecha_hora - timedelta(minutes=usuario_cliente.recordatorio_minutos_antes)
    
    turnos_actuales_servicio = contar_turnos_superpuestos_servicio(db, sucursal_id, servicio_id, fecha_hora, servicio.duracion)

    try:
        # BLOQUEO CRÍTICO
        disponibilidad_valida = (
                db.query(models.Disponibilidad)
                .filter(models.Disponibilidad.id == disponibilidad_valida.id)
                .with_for_update()
                .one()
            )
        
        if len(turnos_actuales_servicio) >= disponibilidad_valida.cant_turnos_max:
            raise exceptions.TurnoSinDisponibilidadError()

        turno = models.Turno(
            usuario_id=usuario_cliente.id if usuario_cliente else None,
            sucursal_id=sucursal_id,
            cliente_id=cliente_id,
            fecha_hora=timezone.to_naive_utc(fecha_hora),
            servicio_id=servicio_id,
            nombre_de_servicio=servicio.nombre,
            duracion=servicio.duracion,
            precio=servicio.precio,
            aclaracion_de_servicio=servicio.aclaracion,
            profesional_id=servicio.profesional_id,
            estado_turno_usuario_id=1, # CONFIRMADO
            estado_turno_sucursal_id=1, # CONFIRMADO
            eliminado_por_usuario=False,
            eliminado_por_sucursal=False,
            recordatorio_fecha_hora=timezone.to_naive_utc(recordatorio_fecha_hora) if recordatorio_fecha_hora else None,
            recordatorio_enviado=False,
        )            
        db.add(turno)

        if cliente.activo == False:
            cliente.activo = True

        db.commit()
    except Exception:
        db.rollback()
        raise

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

def update_estado_turno(db: Session, sucursal_id: int, user: models.Usuario, turno_id: int, turno_update: schemas_sucursal.TurnoUpdateIn):

    db_suc = get_sucursal(db, sucursal_id)
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, user.id, db_suc.empresa.id, sucursal_id)

    turno = db.query(models.Turno).filter_by(
        id=turno_id,
        sucursal_id=db_suc.id, # chequeo que la misma sucursal del turno sea la que hace la request
        eliminado_por_sucursal=False, # chequeo que no esté pasado a historial
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    nuevo_estado = turno_update.estado_turno
    inicio_turno = timezone.ensure_utc(turno.fecha_hora) # convertimos de naive UTC a aware UTC
    email_cancelacion = False

    # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno para luego ponerlo en el turno
    estado_obj = db.query(models.Estado_Turno).filter(
        models.Estado_Turno.estado.ilike(nuevo_estado)).first()

    if not estado_obj:
        raise ValueError("Error al buscar el ID del estado del turno en la tabla estado_turno de la base de datos")
    
    nuevo_estado_check(db, nuevo_estado, inicio_turno, turno.duracion, cancelado_por_usuario=False)

    if turno.estado_turno_sucursal_id != 1: # si no es CONFIRMADO el estado
        raise exceptions.TurnoUpdateStateImmutableError()
    
    servicio = db.query(models.Servicio).filter_by(id=turno.servicio_id, sucursal_id=sucursal_id).first()
    if not servicio:
        raise SucursalServiceNotFoundError()

    if (nuevo_estado == 'CANCELADO_POR_EMPRESA'
        and turno.profesional_id is not None # si tiene profesional
        and turno.profesional_id != user.id
        and servicio.cancelacion_limitada):

        profesional_rol = verificar_rol_en_empresa_o_sucursal(db, turno.profesional_id,
            db_suc.empresa.id, sucursal_id, error=exceptions.EmpresaMiembroNotFoundError())

        if not auxiliares.rol_superior(current_user_rol, profesional_rol):
            raise exceptions.TurnoCanceledByMiembroForbiddenError()

    try:
        turno.estado_turno_sucursal_id = estado_obj.id

        if nuevo_estado == 'CANCELADO_POR_EMPRESA':
            turno.estado_turno_usuario_id = estado_obj.id
            if turno.usuario_id:
                email_cancelacion = True
        else:
            if not turno.usuario_id:
                turno.estado_turno_usuario_id = estado_obj.id

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    # Cargar relaciones importantes antes de mandar mail y devolver
    turno = get_turno(db, turno_id)
    
    if email_cancelacion and turno.usuario:
        try:
            mensajes.send_turno_cancelado_email(
                to_email=turno.usuario.email,
                us_emp_nombre=auxiliares.nombre_empresa(db_suc.empresa.nombre, db_suc.nombre),
                fecha_hora=inicio_turno,
                servicio=turno.nombre_de_servicio,
                motivo=turno_update.observacion)
        except exceptions.EmailSendFailedError:
            pass

    return turno

# Pasa un turno a historial
def delete_turno(db: Session, sucursal_id: int, usuario_id: int, turno_id: int, lista_estados: list):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    
    turno = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_sucursal),
    ).filter_by(
        id=turno_id,
        sucursal_id=sucursal.id,
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    if turno.eliminado_por_sucursal == True:
        return

    # Esto me va a asegurar que el usuario o sucursal tenga que cambiarle el estado a uno de los 
    # posibles para poder eliminar el turno y no que lo elimine sin haber cambiado 
    # el estado previamente y de esta manera, el historial quede con los estados bien puestos
    # (por seguridad si la petición de eliminación llega antes que la de cambio de estado)
    if turno.estado_turno_sucursal.estado not in lista_estados:
        raise exceptions.TurnoDeleteStateConflictError()
    
    try:
        turno.eliminado_por_sucursal = True
        if not turno.usuario_id:
            turno.eliminado_por_usuario = True
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_estados_turnos(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id)
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    turnos = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_sucursal),
    ).filter_by(
        sucursal_id=sucursal_id,
        eliminado_por_sucursal=False,
    ).all()
    
    return turnos

# Devuelve todos los turnos que la sucursal ya completó
'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /sucursales/5/turnos/historial?fecha_hora_ultima=2025-10-10T12:00:00Z&id_ultimo=1234&limit=50
'''
def get_historial(db: Session, sucursal_id: int,
    usuario_id: int, fecha_hora_ultima: datetime | None = None, id_ultimo: int | None = None, limit: int = 50):
    '''
    Devuelve el historial de turnos de una sucursal con paginación.
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
    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    query = db.query(models.Turno).options(
        joinedload(models.Turno.usuario), # usuario relacionado
        joinedload(models.Turno.cliente), # cliente relacionado
        joinedload(models.Turno.profesional), # usuario relacionado (como profesional)
        joinedload(models.Turno.estado_turno_sucursal), # estado del turno de la sucursal
    ).filter(
        models.Turno.sucursal_id == sucursal_id,
        models.Turno.eliminado_por_sucursal == True,
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

def get_servicios(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    # Verificar que el usuario solicitante sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceViewedByEmpleadoError()

    servicios = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades) # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(sucursal_id=sucursal_id).all()

    return servicios

def validar_disponibilidades(disponibilidades):
    # disponibiliades será cualquier lista de objetos a los que se pueda acceeder a sus campos o atributos con .atributo,
    # como, por ejemplo, una lista de objetos models.Disponibilidad con objetos schemas_common.DisponibilidadServicio
    for i, d1 in enumerate(disponibilidades):
        for d2 in disponibilidades[i+1:]:
            if d1.dia == d2.dia:
                if d1.hora_inicio <= d2.hora_fin and d2.hora_inicio <= d1.hora_fin:
                    raise exceptions.SucursalServiceDisponibilidadSuperpuestaError()

def create_servicio(db: Session, sucursal_id: int, usuario_id: int, servicio_nuevo: schemas_sucursal.ServicioCreate):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceCreatedByEmpleadoError()
    
    profesional_id = servicio_nuevo.profesional_id
    
    if profesional_id is not None:
        verificar_rol_en_empresa_o_sucursal(db, profesional_id,
            sucursal.empresa.id, sucursal_id, error=exceptions.EmpresaMiembroNotFoundError())

    # Chequeo si ya existe un servicio igual en la sucursal con el mismo nombre y profesional (tenga o no)
    servicio_existe = db.query(models.Servicio).filter_by(
        sucursal_id=sucursal_id,
        nombre=servicio_nuevo.nombre,
        profesional_id=profesional_id,
    ).first()

    if servicio_existe:
        raise exceptions.SucursalServiceDuplicatedError()

    validar_disponibilidades(servicio_nuevo.disponibilidades)

    try:
        # Crear servicio
        servicio = models.Servicio(
            sucursal_id=sucursal_id,
            nombre=servicio_nuevo.nombre,
            duracion=servicio_nuevo.duracion,
            precio=servicio_nuevo.precio,
            aclaracion=servicio_nuevo.aclaracion,
            profesional_id=profesional_id,
            minutos_min_reserva=servicio_nuevo.minutos_min_reserva,
            dias_max_reserva=servicio_nuevo.dias_max_reserva,
            cancelacion_limitada=servicio_nuevo.cancelacion_limitada,
        )
        db.add(servicio)
        db.flush()  # obtiene servicio.id SIN commit

        if servicio_nuevo.disponibilidades:
            
            # Procesar disponibilidades por día y rango horario
            for disp_range in servicio_nuevo.disponibilidades:
                dia = disp_range.dia
                inicio = disp_range.hora_inicio
                fin = disp_range.hora_fin
                intervalo = disp_range.intervalo
                cant_max = disp_range.cant_turnos_max

                disp = models.Disponibilidad(
                    servicio_id=servicio.id,
                    dia=dia,
                    hora_inicio=inicio,
                    hora_fin=fin,
                    intervalo=intervalo,
                    cant_turnos_max=cant_max,
                )
                db.add(disp)

        db.commit()
    except Exception:
        db.rollback()
        raise

    servicio = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades), # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(id=servicio.id, sucursal_id=sucursal_id).first()

    return servicio

def validar_turnos_existentes_vs_nueva_config(db: Session, servicio: models.Servicio, disponibilidades_finales: list):
    """
    Verifica que los turnos confirmados del servicio
    sigan siendo válidos con la nueva configuración
    de disponibilidades.
    """

    # Traer turnos confirmados del servicio
    turnos_existentes = db.query(models.Turno).filter(
        models.Turno.servicio_id == servicio.id,
        models.Turno.estado_turno_sucursal_id == 1,
        models.Turno.eliminado_por_sucursal == False,
    ).all()

    if not turnos_existentes:
        return  # Nada que validar

    # Agrupar por fecha_hora exacta
    turnos_por_fecha = defaultdict(list)

    for t in turnos_existentes:
        turnos_por_fecha[t.fecha_hora].append(t)

    # Validar cada fecha_hora existente
    for fecha_hora, lista_turnos in turnos_por_fecha.items():

        cant_actual = len(lista_turnos)

        disponibilidad_que_cubre = None

        for d in disponibilidades_finales:
            if disponibilidad_cubre_turno(d, fecha_hora):
                disponibilidad_que_cubre = d
                break

        if disponibilidad_que_cubre is None:
            cant_max = 0
        else:
            cant_max = disponibilidad_que_cubre.cant_turnos_max
        
        dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

        if cant_actual > cant_max and disponibilidad_que_cubre is not None:
            raise exceptions.SucursalServiceUpdateDisponibilidadWithTurnosExistentesError(
                dia=dia,
                hora=hora,
                cant_max=cant_max,
                cant_actual=cant_actual,
            )
        if cant_actual > cant_max and disponibilidad_que_cubre is None:
            raise exceptions.SucursalServiceDeleteDisponibilidadWithTurnosExistentesError(
                dia=dia,
                hora=hora,
                cant_actual=cant_actual,
            )

def update_servicio(db: Session, sucursal_id: int,
    servicio_id: int, usuario_id: int, servicio_update: schemas_sucursal.ServicioUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = servicio_update.dict(exclude_unset=True)

    try:
        # Traer servicio a actualizar
        servicio = db.query(models.Servicio).filter_by(id=servicio_id, sucursal_id=sucursal_id).with_for_update().first()
        if not servicio:
            raise exceptions.SucursalServiceNotFoundError()

        # Chequeo si ya existe otro servicio en la sucursal con el mismo nombre y profesional (tenga o no)
        nombre_nuevo = update_data.get("nombre", servicio.nombre) # Si no vino, uso el nombre que ya estaba
        profesional_id_nuevo = update_data.get("profesional_id", servicio.profesional_id) # Si no vino, uso el profesional_id que ya estaba
        
        if profesional_id_nuevo is not None:
            verificar_rol_en_empresa_o_sucursal(db, profesional_id_nuevo,
                sucursal.empresa.id, sucursal_id, error=exceptions.EmpresaMiembroNotFoundError())

        servicio_existe = db.query(models.Servicio).filter(
            models.Servicio.id != servicio_id,
            models.Servicio.sucursal_id == sucursal_id,
            models.Servicio.nombre == nombre_nuevo,
            models.Servicio.profesional_id == profesional_id_nuevo,
        ).first()
        
        if servicio_existe:
            raise exceptions.SucursalServiceDuplicatedError()

        # Actualizar campos simples (excepto disponibilidades)
        for attr, value in update_data.items():
            if attr == "disponibilidades":
                continue
            setattr(servicio, attr, value) # Si value es None, se actualiza; si no existe en dict, se ignora

        if "disponibilidades" in update_data:

            def disp_key(d):
                return (
                    d.dia,
                    d.hora_inicio,
                    d.hora_fin,
                    d.intervalo,
                    d.cant_turnos_max,
                )
            
            class DispTemp:
                def __init__(self, dia, hora_inicio, hora_fin, intervalo, cant_turnos_max):
                    self.dia = dia
                    self.hora_inicio = hora_inicio
                    self.hora_fin = hora_fin
                    self.intervalo = intervalo
                    self.cant_turnos_max = cant_turnos_max

            # Disponibilidades actuales en BD
            disps_db = db.query(models.Disponibilidad).filter(
                models.Disponibilidad.servicio_id == servicio.id,
            ).order_by(models.Disponibilidad.id.asc()).with_for_update().all()

            # diccionario de clave una tupla y valor un models.Disponibilidad con todas las disponibilidades que tiene la base actualmente
            db_map = {disp_key(d): d for d in disps_db}

            # Disponibilidades del JSON
            # json_map va a ser un diccionario de clave una tupla y valor un diccionario con todas las disponibilidades que vienen del front
            json_map = {}
            for d in update_data["disponibilidades"]: # update_data["disponibilidades"] es una lista de diccionarios
                key = (
                    d["dia"],
                    d["hora_inicio"],
                    d["hora_fin"],
                    d["intervalo"],
                    d["cant_turnos_max"],
                )
                json_map[key] = d
            
            permanecen = [
                disp_db
                for key, disp_db in db_map.items()
                if key in json_map
            ] # list[models.Disponibilidad] de las disponibilidades que van a quedar en la base de datos y no se van a borrar
            
            nuevas = [
                DispTemp(
                    d["dia"],
                    d["hora_inicio"],
                    d["hora_fin"],
                    d["intervalo"],
                    d["cant_turnos_max"],
                )
                for key, d in json_map.items()
                if key not in db_map
            ] # list[DispTemp] de las disponibilidades nuevas que vienen del front y que se van a colocar en la base

            disponibilidades_finales_que_quedaran_en_la_base = permanecen + nuevas

            validar_disponibilidades(disponibilidades_finales_que_quedaran_en_la_base)

            validar_turnos_existentes_vs_nueva_config(
                db,
                servicio,
                disponibilidades_finales_que_quedaran_en_la_base,
            )

            # Borrar las que ya no están
            for key, disp_db in db_map.items():
                if key not in json_map:
                    # si los mismos valores (campos) de la disponibilidad no están en la
                    # configuración final (determinada por las disponibilidades que vienen del front) y
                    # sí está en la base de datos, se borra la disponibilidad
                    db.delete(disp_db)

            # Agregar las nuevas
            for key, disp_json in json_map.items():
                if key not in db_map:
                    # si los mismos valores (campos) de la disponibilidad no están en la
                    # configuración inicial (determinada por las disponibilidades que ya estaban en la base de datos) y
                    # sí está en la json que viene ddel front, se agrega la disponibilidad
                    db.add(
                        models.Disponibilidad(
                            servicio_id=servicio.id,
                            dia=disp_json["dia"],
                            hora_inicio=disp_json["hora_inicio"],
                            hora_fin=disp_json["hora_fin"],
                            intervalo=disp_json["intervalo"],
                            cant_turnos_max=disp_json["cant_turnos_max"],
                        )
                    )

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    servicio = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades), # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(id=servicio_id, sucursal_id=sucursal_id).first()

    return servicio

def delete_servicios(db: Session, sucursal_id: int, usuario_id: int, servicios_delete: list[int]):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceDeletedByEmpleadoError()
    
    try:
        # Ordenar para evitar deadlocks
        servicios_delete.sort()

        # Bloquear todos los servicios primero
        servicios = (
            db.query(models.Servicio)
            .filter(
                models.Servicio.id.in_(servicios_delete),
                models.Servicio.sucursal_id == sucursal_id,
            )
            .order_by(models.Servicio.id.asc())
            .with_for_update()
            .all()
        )

        if len(servicios) != len(servicios_delete):
            raise exceptions.SucursalServiceNotFoundError()

        # Validar que no tengan turnos confirmados
        for servicio in servicios:
            turno_confirmado = db.query(models.Turno).filter(
                models.Turno.servicio_id == servicio.id,
                models.Turno.estado_turno_sucursal_id == 1,
            ).first()

            if turno_confirmado:
                raise exceptions.SucursalServiceConTurnosConfirmadosError()

        # Borrar servicios en otro bucle for para separar responsabilidades (primero validar y después ejecutar todo)
        for servicio in servicios:
            db.delete(servicio) # CASCADE borra disponibilidades

        db.commit()
    except Exception:
        db.rollback()
        raise

def get_miembros(db: Session, sucursal_id: int, usuario_solicitante_id: int):

    get_sucursal(db, sucursal_id, error_if_not_active=False)

    # Verificar que el usuario solicitante sea gerente de sucursal
    current_user_rol = verificar_rol_en_sucursal(db, usuario_solicitante_id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaMiembrosViewedByEmpleadoError()

    miembros = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario)).filter_by(sucursal_id=sucursal_id).all()

    return miembros

def get_miembro_sucursal(db: Session, sucursal_id: int, usuario_miembro_id: int):

    miembro_sucursal = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.sucursal)).filter_by(
            usuario_id=usuario_miembro_id, sucursal_id=sucursal_id).first()

    if not miembro_sucursal:
        raise exceptions.SucursalMiembroNotFoundError()

    return miembro_sucursal

# El usuario de la sucursal se borra de esta
def leave_sucursal(db: Session, sucursal_id: int, usuario_id: int):

    get_sucursal(db, sucursal_id)

    verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    # Traer el objeto de clase Miembro_Sucursal que se eliminará
    miembro_sucursal = get_miembro_sucursal(db, sucursal_id, usuario_id)

    servicios = db.query(models.Servicio).filter(
        models.Servicio.sucursal_id == sucursal_id,
        models.Servicio.profesional_id == usuario_id).all()

    try:
        for servicio in servicios:

            turno_confirmado = db.query(models.Turno).filter(
                models.Turno.servicio_id == servicio.id,
                models.Turno.estado_turno_sucursal_id == 1,
            ).first()

            if turno_confirmado:
                raise exceptions.SucursalProfesionalConTurnosConfirmadosOutError()

            db.delete(servicio)
        
        db.delete(miembro_sucursal)
        db.commit()
    except Exception:
        db.rollback()
        raise

def add_miembro(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario o gerente de empresa
    verificar_rol_en_empresa(db, usuario_solicitante_id, sucursal.empresa.id)

    # Traer al menos un objeto de clase Miembro_Sucursal para comprobar que ya está en alguna sucursal al menos
    es_miembro_de_alguna_sucursal = db.query(models.Miembro_Sucursal).join(models.Sucursal).filter(
        models.Miembro_Sucursal.usuario_id == target_id,
        models.Sucursal.empresa_id == sucursal.empresa.id).first()

    if not es_miembro_de_alguna_sucursal:
        raise SucursalMiembroAddError()
    
    # Traer el objeto de clase Miembro_Sucursal para ver si ya existe
    miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id)
    if not miembro_sucursal_target:

        db_nuevo_rol = auxiliares.transformar_rol(nuevo_rol, contexto="sucursal") # int
        
        try:
            miembro = models.Miembro_Sucursal(
                usuario_id=target_id,
                sucursal_id=sucursal_id,
                rol=db_nuevo_rol,
            )
            db.add(miembro)
            db.commit()
        except Exception:
            db.rollback()
            raise
    
    miembro_sucursales = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.sucursal)).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

    return miembro_sucursales

# Esta función es solo para que un propietario pueda modificar un rol de gerente de sucursal o empleado
# o para que un gerente de empresa pueda modificar un rol de gerente de sucursal o empleado sin que este
# pueda ascender a uno a gerente de empresa o propietario
def update_rol(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario o gerente de empresa. Esta función es un recurso global de empresa porque
    # los gerentes de sucursal no pueden modificar empleados ya que significaría que los ascenderían y eso no se puede. Además,
    # los gerentes (de empresa o de sucursal) no pueden modificar a sus pares o superiores. En caso de que se agregue un rol
    # intermedio entre empleado y gerente de sucursal, recién ahí, la función dejaría de ser global y debería hacerse un
    # verificar_rol_en_empresa_o_sucursal además de poner la prohibición de modificación de roles para empleados y este nuevo rol.
    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, sucursal.empresa.id)
    
    roles_empresas = ['propietario', 'gerente_empresa']
    
    if current_user_rol == 'gerente_empresa' and nuevo_rol in roles_empresas:
        raise exceptions.EmpresaRolUpdateError()
    
    # Traer el objeto de clase Miembro_Sucursal al que se le modificará el rol
    miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id)
    
    try:
        if nuevo_rol in roles_empresas: # signifca que un gerente de sucursal o empleado pasa a ser gerente de empresa o propietario

            db_nuevo_rol = auxiliares.transformar_rol(nuevo_rol, contexto="empresa") # int

            miembro = models.Miembro_Empresa(
                usuario_id=target_id,
                empresa_id=sucursal.empresa.id,
                rol=db_nuevo_rol,
            )
            db.add(miembro)
            db.delete(miembro_sucursal_target)
            db.commit()

            return miembro

        else: # signifca que un gerente de sucursal pasa a ser empleado o viceversa

            db_nuevo_rol = auxiliares.transformar_rol(nuevo_rol, contexto="sucursal") # int

            miembro_sucursal_target.rol = db_nuevo_rol
            db.commit()

            miembro_sucursales = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.usuario),
                joinedload(models.Miembro_Sucursal.sucursal)).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

            return miembro_sucursales

    except Exception:
        db.rollback()
        raise

def delete_miembro(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)

    if usuario_solicitante_id == target_id:
        raise exceptions.SucursalInvalidSelfRemovalError()

    # Traer el objeto de clase Miembro_Sucursal que se eliminará
    miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id)

    miembro_sucursal_target_rol = auxiliares.transformar_rol(miembro_sucursal_target.rol, contexto="sucursal") # string

    if not auxiliares.rol_superior(current_user_rol, miembro_sucursal_target_rol):
        raise exceptions.EmpresaMiembroDeleteError()
    
    servicios = db.query(models.Servicio).join(models.Sucursal).filter(
        models.Servicio.sucursal_id == sucursal_id,
        models.Servicio.profesional_id == target_id).all()
    
    try:
        for servicio in servicios:

            turno_confirmado = db.query(models.Turno).filter(
                models.Turno.servicio_id == servicio.id,
                models.Turno.estado_turno_sucursal_id == 1,
            ).first()

            if turno_confirmado:
                raise exceptions.SucursalMiembroDeleteConTurnosConfirmadosError()

            db.delete(servicio)

        db.delete(miembro_sucursal_target)

        db.commit()

    except Exception:
        db.rollback()
        raise

def get_clientes_bloqueados(db: Session, sucursal_id: int, usuario_solicitante_id: int):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)

    bloqueos = db.query(models.BloqueoSucursal).options(
        joinedload(models.BloqueoSucursal.cliente),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(sucursal_id=sucursal_id).all()

    miembros_empresa = db.query(models.Miembro_Empresa).filter_by(empresa_id=sucursal.empresa.id).all()

    miembros_sucursal = db.query(models.Miembro_Sucursal).filter_by(sucursal_id=sucursal_id).all()

    miembros_empresa_map = {
        m.usuario_id: m
        for m in miembros_empresa
    }

    miembros_sucursal_map = {
        m.usuario_id: m
        for m in miembros_sucursal
    }

    resultados = []

    for b in bloqueos:
        miembro_rol = None

        if b.created_by_id in miembros_empresa_map:
            m = miembros_empresa_map[b.created_by_id]
            miembro_rol = auxiliares.transformar_rol(m.rol, contexto="empresa") # string

        elif b.created_by_id in miembros_sucursal_map:
            m = miembros_sucursal_map[b.created_by_id]
            miembro_rol = auxiliares.transformar_rol(m.rol, contexto="sucursal") # string

        resultados.append((b, miembro_rol))

    return resultados

def block_cliente(db: Session, sucursal_id: int, usuario_solicitante_id: int, cliente_id: int, motivo: str | None):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()
    
    bloqueo = db.query(models.BloqueoSucursal).options(
        joinedload(models.BloqueoSucursal.cliente),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(sucursal_id=sucursal_id, cliente_id=cliente_id).first()

    if bloqueo:
        return bloqueo, current_user_rol

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    try:
        nuevo_bloqueo = models.BloqueoSucursal(
            sucursal_id=sucursal_id,
            cliente_id=cliente_id,
            created_by_id=usuario_solicitante_id,
            motivo=motivo,
            created_at=ahora_utc,
        )
        db.add(nuevo_bloqueo)
        db.commit()
    except Exception:
        db.rollback()
        raise

    bloqueo = db.query(models.BloqueoSucursal).options(
        joinedload(models.BloqueoSucursal.cliente),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(id=nuevo_bloqueo.id).first()
    
    return bloqueo, current_user_rol

def unlock_cliente(db: Session, sucursal_id: int, usuario_solicitante_id: int, cliente_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'empleado':
        raise exceptions.SucursalClienteUnlockedByEmpleadoError()

    cliente = db.query(models.Cliente).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()
    
    bloqueo = db.query(models.BloqueoSucursal).filter_by(sucursal_id=sucursal_id, cliente_id=cliente_id).first()
    if not bloqueo:
        return # si no estaba bloqueado, se responde con éxito igual
    
    try:
        db.delete(bloqueo)
        db.commit()
    except Exception:
        db.rollback()
        raise