from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import UploadFile
from fastapi.exceptions import RequestValidationError
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload, selectinload
import cloudinary.uploader

from crud.common import (
    get_empresa,
    get_sucursal,
    verificar_rol_en_empresa,
    verificar_rol_en_sucursal,
    verificar_rol_en_empresa_o_sucursal,
    disponibilidad_cubre_turno,
    nuevo_estado_check,
    contar_turnos_superpuestos_servicio,
    tiene_turno_superpuesto,
    crear_extra_data_notificacion,
    guardar_notificacion,
)
from core import models, constantes, exceptions, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import sucursal as schemas_sucursal

def create(db: Session, usuario_id: int, nueva_sucursal: schemas_sucursal.SucursalCreate):

    empresa = get_empresa(db, nueva_sucursal.empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa.id)

    if current_user_rol != 'PROPIETARIO':
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
    if current_user_rol == 'EMPLEADO':
        raise exceptions.EmpresaUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = sucursal_update.model_dump(exclude_unset=True)

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

    if current_user_rol != 'PROPIETARIO':
        raise exceptions.SucursalDeactivateForbiddenError()
    
    try:
        # Bloquear todos los servicios primero
        servicios_base = (
            db.query(models.ServicioBase)
            .filter(
                models.ServicioBase.sucursal_id == sucursal_id,
            )
            .order_by(models.ServicioBase.id.asc())
            .with_for_update()
            .all()
        )

        ids_servicios_base = [s.id for s in servicios_base]

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(ids_servicios_base),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )
    
        turno_confirmado = db.query(models.Turno).filter(
            models.Turno.sucursal_id == sucursal_id,
            models.Turno.eliminado_por_sucursal == False,
            models.Turno.estado_turno_sucursal_id == 1,
        ).first()

        if turno_confirmado:
            raise exceptions.SucursalDeactivateWithTurnosConfirmadosError()

        sucursal.activa = False
        db.commit()
    except Exception:
        db.rollback()
        raise

def reactivate(db: Session, sucursal_id: int, usuario_id: int):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    # verificar permisos
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, sucursal.empresa.id)

    if current_user_rol != 'PROPIETARIO':
        raise exceptions.SucursalActivateForbiddenError()

    try:
        sucursal.activa = True
        db.commit()
    except Exception:
        db.rollback()
        raise

'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /sucursales/5/clientes?search=gonzalez&activo=true&id_ultimo=1234&limit=50
'''
def get_clientes(db: Session, sucursal_id: int,
    usuario_id: int, search: str | None = None, activo: bool | None = None, id_ultimo: int | None = None, limit: int = 50):
    '''
    Devuelve los clientes de una sucursal con paginación.
    Van ordenados del más reciente creado al más antiguo (fecha descendente).

    Parámetros:
        search: filtra según alguna coincidencia con este string (contiene el string) (puede ser dni, nombre, apellido, etc.).
        activo: filtra según si el usuario pidió solo clientes activos, inactivos o cualquiera de los dos.
        id_ultimo: id del último cliente recibido (para la siguiente página).
        limit: cantidad máxima de clientes a devolver (máx 100).
    
    Proceso:
        Primera solicitud (en login): front no envía cursor → back devuelve primeros N registros + cursor del último.
        Siguientes solicitudes: front envía cursor → back devuelve los siguientes N registros + cursor actualizado.
        Última página: back devuelve lista vacía y cursor None → front deja de pedir más.
    '''
    db_suc = get_sucursal(db, sucursal_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_id, db_suc.empresa.id, sucursal_id)

    query = db.query(models.Cliente).options(
        joinedload(models.Cliente.bloqueo),
    ).filter(models.Cliente.sucursal_id == sucursal_id)

    # Filtro por activo (IMPORTANTE usar is not None)
    if activo is not None:
        query = query.filter(models.Cliente.activo == activo)

    # Cursor de paginación
    if id_ultimo is not None:
        query = query.filter(models.Cliente.id < id_ultimo)

    # Búsqueda global
    if search:
        search = auxiliares.quitar_acentos(search.lower())
        palabra = f"%{search}%"

        query = query.filter(
            models.Cliente.busqueda_texto.ilike(palabra)
        )

    # Orden descendente para que el más reciente (id más grande) sea el primero de la lista
    clientes = query.order_by(models.Cliente.id.desc()).limit(limit).all()

    # Nuevo cursor
    ultimo_cursor_id = clientes[-1].id if clientes else None

    return clientes, ultimo_cursor_id

def create_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_nuevo: schemas_sucursal.ClienteCreate):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    email_normalizado = models.normalizar_email(cliente_nuevo.email)

    # Chequeo si ya existe un cliente igual en la sucursal con el mismo email
    cliente_existe = db.query(models.Cliente).filter_by(
        sucursal_id=sucursal_id,
        email_normalizado=email_normalizado,
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
    
    cliente = db.query(models.Cliente).options(
        joinedload(models.Cliente.bloqueo),
    ).filter(models.Cliente.id == cliente.id).first()

    return cliente

def update_cliente(db: Session, sucursal_id: int, usuario_id: int, cliente_id: int, cliente_update: schemas_sucursal.ClienteUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)

    cliente = db.query(models.Cliente).options(
        joinedload(models.Cliente.bloqueo),
    ).filter_by(
        id=cliente_id,
        sucursal_id=sucursal_id,
    ).first()

    if not cliente:
        raise exceptions.ClienteNotFoundError()
    
    # Convertir a dict solo con campos enviados
    update_data = cliente_update.model_dump(exclude_unset=True)

    # Chequeo si ya existe otro cliente en la sucursal con el mismo email
    email_nuevo = update_data.get("email", cliente.email) # Si no vino, uso el email que ya estaba

    email_nuevo_normalizado = models.normalizar_email(email_nuevo)

    cliente_existe = db.query(models.Cliente).filter(
        models.Cliente.id != cliente_id,
        models.Cliente.sucursal_id == sucursal_id,
        models.Cliente.email_normalizado == email_nuevo_normalizado,
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

    try:
        cliente = db.query(models.Cliente).filter_by(
            id=cliente_id,
            sucursal_id=sucursal_id,
        ).with_for_update().first()

        if not cliente:
            raise exceptions.ClienteNotFoundError()
        
        turno_confirmado = db.query(models.Turno).filter(
            models.Turno.sucursal_id == sucursal_id,
            models.Turno.eliminado_por_sucursal == False,
            models.Turno.estado_turno_sucursal_id == 1,
            models.Turno.cliente_id == cliente_id,
        ).first()

        if turno_confirmado:
            raise exceptions.ClienteDeactivateWithTurnosConfirmadosError()

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

def reservar_turno(db: Session, sucursal_id: int, usuario_miembro_id: int, reserva: schemas_usuario.ReservaTurnoSucursalIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa_o_sucursal(db, usuario_miembro_id, sucursal.empresa.id, sucursal_id)

    cliente_id = reserva.cliente_id
    servicio_id = reserva.servicio_id
    fecha_hora = reserva.fecha_hora

    dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)
    fecha_local = timezone.utc_to_local(fecha_hora).date()

    cliente_email_normalizado = models.normalizar_email(cliente.email)

    try:
        cliente = db.query(models.Cliente).filter_by(
            id=cliente_id,
            sucursal_id=sucursal_id,
        ).first()

        if not cliente:
            raise exceptions.ClienteNotFoundError()

        bloqueo = db.query(models.BloqueoSucursal).filter_by(sucursal_id=sucursal_id, cliente_id=cliente_id).first()
        if bloqueo:
            raise exceptions.SucursalClienteBlockedError()
        
        usuario_cliente = db.query(models.Usuario).filter_by(email_normalizado=cliente_email_normalizado).first()

        turnos_actuales_usuario_cliente = []

        if usuario_cliente:
            turnos_actuales_usuario_cliente = db.query(models.Turno).filter_by(
                usuario_id=usuario_cliente.id,
                eliminado_por_usuario=False,
                estado_turno_usuario_id=1, # solo turnos confirmados cuento
            ).all()
        
        servicio = (
            db.query(models.Servicio)
            .join(models.ServicioBase)
            .filter(
                models.Servicio.id == servicio_id,
                models.Servicio.vigente_desde <= fecha_local,
                or_(
                    models.Servicio.vigente_hasta.is_(None),
                    models.Servicio.vigente_hasta >= fecha_local,
                ),
                models.ServicioBase.sucursal_id == sucursal_id,
            )
            .first()
        )

        if not servicio:
            raise exceptions.SucursalServiceNotFoundError()

        servicio = (
            db.query(models.Servicio)
            .join(models.ServicioBase)
            .join(models.Disponibilidad)
            .options(
                joinedload(models.Servicio.servicio_base).joinedload(models.ServicioBase.profesional),
                selectinload(models.Servicio.disponibilidades),
            )
            .filter(
                models.Servicio.id == servicio_id,
                models.Servicio.vigente_desde <= fecha_local,
                or_(
                    models.Servicio.vigente_hasta.is_(None),
                    models.Servicio.vigente_hasta >= fecha_local,
                ),
                models.ServicioBase.sucursal_id == sucursal_id,
                models.Disponibilidad.dia == dia,
                models.Disponibilidad.hora_inicio <= hora,
                models.Disponibilidad.hora_fin >= hora,
            )
            .first()
        )

        if not servicio:
            raise exceptions.TurnoReservaDisponibilidadNoConfiguradaError()
        
        excepcion_fecha_servicio = (
            db.query(models.ExcepcionFechaServicio)
            .filter(
                models.ExcepcionFechaServicio.servicio_base_id == servicio.servicio_base.id,
                models.ExcepcionFechaServicio.fecha_inicio <= fecha_local,
                models.ExcepcionFechaServicio.fecha_fin >= fecha_local,
            )
            .first()
        )

        if excepcion_fecha_servicio:
            raise exceptions.SucursalReservaExceptionDateServiceError(motivo=excepcion_fecha_servicio.motivo)
        
        # Validar límite máximo de días
        if servicio.servicio_base.dias_max_reserva is not None:
            validar_turno_dias_max = timezone.validar_turno_dias_max(fecha_hora, servicio.servicio_base.dias_max_reserva)
            if not validar_turno_dias_max:
                raise exceptions.TurnoReservaFueraDeRangoError(dias_max=servicio.servicio_base.dias_max_reserva)
        
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
        
        if servicio.servicio_base.profesional_id is not None:

            turnos_actuales_profesional = db.query(models.Turno).filter_by(
                profesional_id=servicio.servicio_base.profesional_id,
                estado_turno_sucursal_id=1, # solo turnos confirmados cuento
            ).all()

            conflicto_profesional = tiene_turno_superpuesto(turnos_actuales_profesional, fecha_hora, servicio.duracion)

            if conflicto_profesional:
                raise exceptions.TurnoProfesionalOverlappingAppointmentError(
                    apellido=servicio.servicio_base.profesional.apellido,
                    nombre=servicio.servicio_base.profesional.nombre,
                )
        
        recordatorio_fecha_hora = None

        if usuario_cliente:
            if usuario_cliente.recordatorio_minutos_antes is not None:
                recordatorio_fecha_hora = fecha_hora - timedelta(minutes=usuario_cliente.recordatorio_minutos_antes)

        # BLOQUEO CRÍTICO
        disponibilidad_valida = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.id == disponibilidad_valida.id)
            .with_for_update()
            .one()
        )

        turnos_actuales_servicio = contar_turnos_superpuestos_servicio(db, sucursal_id, servicio_id, fecha_hora, servicio.duracion)
        
        if len(turnos_actuales_servicio) >= disponibilidad_valida.cant_turnos_max:
            raise exceptions.TurnoSinDisponibilidadError()

        # Chequeo que la sucursal siga activa por si en el medio de la transacción justo se desactivó
        db.refresh(sucursal)
        if not sucursal.activa:
            raise exceptions.SucursalDeactivatedError()

        turno = models.Turno(
            usuario_id=usuario_cliente.id if usuario_cliente else None,
            sucursal_id=sucursal_id,
            cliente_id=cliente_id,
            fecha_hora=timezone.to_naive_utc(fecha_hora),
            servicio_id=servicio_id,
            nombre_de_servicio=servicio.servicio_base.nombre,
            duracion=servicio.duracion,
            precio=servicio.precio,
            aclaracion_de_servicio=servicio.servicio_base.aclaracion,
            profesional_id=servicio.servicio_base.profesional_id,
            created_at=timezone.to_naive_utc(timezone.now_utc()),
            estado_turno_usuario_id=1, # CONFIRMADO
            estado_turno_sucursal_id=1, # CONFIRMADO
            eliminado_por_usuario=False,
            eliminado_por_sucursal=False,
            recordatorio_fecha_hora=timezone.to_naive_utc(recordatorio_fecha_hora) if recordatorio_fecha_hora else None,
            recordatorio_enviado=False,
        )            
        db.add(turno)
        db.flush()

        if cliente.activo == False:
            cliente.activo = True

        if usuario_cliente:
            nombre_empresa = auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre)
            cuando = auxiliares.formatear_fecha_hora_turno(fecha_hora)

            extra_data = crear_extra_data_notificacion(turno_id=turno.id, nombre_empresa=nombre_empresa, cuando=cuando)
            guardar_notificacion(db, usuario_cliente.id, "TURNO_NUEVO_USUARIO", extra_data)

            if recordatorio_fecha_hora:
                guardar_notificacion(
                    db,
                    usuario_cliente.id,
                    "RECORDATORIO_USUARIO",
                    extra_data,
                    fecha_hora_minima_de_envio=recordatorio_fecha_hora,
                )

        db.commit()
    except Exception:
        db.rollback()
        raise

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

def update_estado_turno(db: Session, sucursal_id: int, user: models.Usuario, turno_id: int, turno_update: schemas_sucursal.TurnoUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, user.id, sucursal.empresa.id, sucursal_id)

    turno = db.query(models.Turno).filter_by(
        id=turno_id,
        sucursal_id=sucursal.id, # chequeo que la misma sucursal del turno sea la que hace la request
        eliminado_por_sucursal=False, # chequeo que no esté pasado a historial
    ).first()

    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    nuevo_estado = turno_update.estado_turno
    inicio_turno = timezone.ensure_utc(turno.fecha_hora) # convertimos de naive UTC a aware UTC
    email_cancelacion = False

    # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno para luego ponerlo en el turno
    estado_obj = db.query(models.Estado_Turno).filter(
        models.Estado_Turno.estado.ilike(nuevo_estado),
    ).first()

    if not estado_obj:
        raise ValueError("Error al buscar el ID del estado del turno en la tabla estado_turno de la base de datos")
    
    nuevo_estado_check(db, nuevo_estado, inicio_turno, turno.duracion, cancelado_por_usuario=False)

    if turno.estado_turno_sucursal_id != 1: # si no es CONFIRMADO el estado
        raise exceptions.TurnoUpdateStateImmutableError()
    
    servicio = (
        db.query(models.Servicio)
        .join(models.ServicioBase)
        .options(
            joinedload(models.Servicio.servicio_base).joinedload(models.ServicioBase.profesional),
        )
        .filter(
            models.Servicio.id == turno.servicio_id,
            models.ServicioBase.sucursal_id == sucursal_id,
        )
        .first()
    )
    if not servicio:
        raise exceptions.SucursalServiceNotFoundError()

    if (nuevo_estado == 'CANCELADO_POR_EMPRESA'
        and turno.profesional_id is not None # si tiene profesional
        and turno.profesional_id != user.id
        and servicio.servicio_base.cancelacion_limitada
    ):
        profesional_rol = verificar_rol_en_empresa_o_sucursal(
            db,
            turno.profesional_id,
            sucursal.empresa.id,
            sucursal_id,
            error=exceptions.EmpresaMiembroNotFoundError(),
        )

        if not auxiliares.rol_superior(current_user_rol, profesional_rol):
            raise exceptions.TurnoCanceledByMiembroForbiddenError()

    try:
        turno.estado_turno_sucursal_id = estado_obj.id

        if nuevo_estado == 'CANCELADO_POR_EMPRESA':
            turno.estado_turno_usuario_id = estado_obj.id
            if turno.usuario_id:
                email_cancelacion = True

                db.query(models.Notificacion).filter(
                    models.Notificacion.usuario_id == turno.usuario_id,
                    models.Notificacion.tipo == "RECORDATORIO_USUARIO",
                    models.Notificacion.extra_data["turno_id"].as_integer() == turno_id,
                ).delete(synchronize_session=False)

                cuando = auxiliares.formatear_fecha_hora_turno(turno.fecha_hora)
                nombre_empresa = auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre)

                extra_data = crear_extra_data_notificacion(turno_id=turno.id, nombre_empresa=nombre_empresa, cuando=cuando)
                guardar_notificacion(db, turno.usuario_id, "TURNO_CANCELADO_USUARIO", extra_data)
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
                us_emp_nombre=nombre_empresa,
                fecha_hora=inicio_turno,
                servicio=turno.nombre_de_servicio,
                motivo=turno_update.observacion,
            )
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
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceViewedByEmpleadoError()

    servicios_base = db.query(models.ServicioBase).options(
        joinedload(models.ServicioBase.profesional),
        selectinload(models.ServicioBase.servicios).selectinload(models.Servicio.disponibilidades),
        selectinload(models.ServicioBase.excepciones_fechas),
    ).filter_by(sucursal_id=sucursal_id).all()

    return servicios_base

def validar_disponibilidades(disponibilidades):
    # disponibiliades será cualquier lista de objetos a los que se pueda acceeder a sus campos o atributos con .atributo,
    # como, por ejemplo, una lista de objetos models.Disponibilidad con objetos schemas_common.DisponibilidadServicio
    for i, d1 in enumerate(disponibilidades):
        for d2 in disponibilidades[i+1:]:
            if d1.dia == d2.dia:
                if d1.hora_inicio <= d2.hora_fin and d2.hora_inicio <= d1.hora_fin:
                    raise exceptions.SucursalServiceDisponibilidadSuperpuestaError()

def create_servicio_base(db: Session, sucursal_id: int, usuario_id: int, servicio_nuevo: schemas_sucursal.ServicioBaseCreate):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceCreatedByEmpleadoError()
    
    profesional_id = servicio_nuevo.profesional_id
    
    if profesional_id is not None:
        verificar_rol_en_empresa_o_sucursal(
            db,
            profesional_id,
            sucursal.empresa.id,
            sucursal_id,
            error=exceptions.EmpresaMiembroNotFoundError(),
        )

    servicio_base_existe = db.query(models.ServicioBase).filter(
        models.ServicioBase.sucursal_id == sucursal_id,
        models.ServicioBase.nombre == servicio_nuevo.nombre,
        models.ServicioBase.profesional_id == profesional_id,
    ).first()

    if servicio_base_existe:
        raise exceptions.SucursalServiceAlreadyExistsError()

    validar_disponibilidades(servicio_nuevo.disponibilidades)

    try:
        servicio_base = models.ServicioBase(
            sucursal_id=sucursal_id,
            nombre=servicio_nuevo.nombre,
            aclaracion=servicio_nuevo.aclaracion,
            profesional_id=profesional_id,
            minutos_min_reserva=servicio_nuevo.minutos_min_reserva,
            dias_max_reserva=servicio_nuevo.dias_max_reserva,
            cancelacion_limitada=servicio_nuevo.cancelacion_limitada,
        )
        db.add(servicio_base)
        db.flush() # obtiene servicio_base.id sin commit

        servicio = models.Servicio(
            servicio_base_id=servicio_base.id,
            duracion=servicio_nuevo.duracion,
            precio=servicio_nuevo.precio,
            vigente_desde=servicio_nuevo.vigente_desde,
            vigente_hasta=servicio_nuevo.vigente_hasta,
            created_at=timezone.to_naive_utc(timezone.now_utc()),
        )
        db.add(servicio)
        db.flush() # obtiene servicio.id sin commit

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

    servicio_base = db.query(models.ServicioBase).options(
        joinedload(models.ServicioBase.profesional),
        selectinload(models.ServicioBase.servicios).selectinload(models.Servicio.disponibilidades),
        selectinload(models.ServicioBase.excepciones_fechas),
    ).filter_by(id=servicio_base.id, sucursal_id=sucursal_id).first()

    return servicio_base

def update_servicio_base(db: Session, sucursal_id: int,
    usuario_id: int, servicio_base_id: int, servicio_update: schemas_sucursal.ServicioBaseUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = servicio_update.model_dump(exclude_unset=True)

    try:
        servicio_base = db.query(models.ServicioBase).filter_by(id=servicio_base_id, sucursal_id=sucursal_id).with_for_update().first()
        if not servicio_base:
            raise exceptions.SucursalServiceNotFoundError()

        # Chequeo si ya existe otro servicio en la sucursal con el mismo nombre y profesional (tenga o no)
        nombre_nuevo = update_data.get("nombre", servicio_base.nombre) # si no vino, uso el nombre que ya estaba

        servicio_base_existe = db.query(models.ServicioBase).filter(
            models.ServicioBase.id != servicio_base_id,
            models.ServicioBase.sucursal_id == sucursal_id,
            models.ServicioBase.nombre == nombre_nuevo,
            models.ServicioBase.profesional_id == servicio_base.profesional_id,
        ).first()
        
        if servicio_base_existe:
            raise exceptions.SucursalServiceAlreadyExistsError()

        # Actualizar campos
        for attr, value in update_data.items():
            setattr(servicio_base, attr, value) # si value es None, se actualiza; si no existe en dict, se ignora

        db.commit()
    except Exception:
        db.rollback()
        raise

    servicio_base = db.query(models.ServicioBase).options(
        joinedload(models.ServicioBase.profesional),
        selectinload(models.ServicioBase.servicios).selectinload(models.Servicio.disponibilidades),
        selectinload(models.ServicioBase.excepciones_fechas),
    ).filter_by(id=servicio_base.id, sucursal_id=sucursal_id).first()

    return servicio_base

def delete_servicios_base(db: Session, sucursal_id: int, usuario_id: int, servicios_delete: list[int]):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceDeletedByEmpleadoError()
    
    try:
        # Bloquear todos los servicios primero
        servicios_base = (
            db.query(models.ServicioBase)
            .filter(
                models.ServicioBase.id.in_(servicios_delete),
                models.ServicioBase.sucursal_id == sucursal_id,
            )
            .order_by(models.ServicioBase.id.asc())
            .with_for_update()
            .all()
        )

        if len(servicios_base) != len(servicios_delete):
            raise exceptions.SucursalServiceNotFoundError()

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(servicios_delete),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        # Validar que no tengan turnos confirmados
        turno_confirmado = (
            db.query(models.Turno.id)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.SucursalServiceDeleteWithTurnosConfirmadosError()

        for servicio_base in servicios_base:
            db.delete(servicio_base) # CASCADE borra servicios versionados (con sus disponibilidades) y excepciones

        db.commit()
    except Exception:
        db.rollback()
        raise

def create_servicio_version(db: Session, sucursal_id: int,
    usuario_id: int, servicio_base_id: int, servicio_nuevo: schemas_sucursal.ServicioCreate):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceCreatedByEmpleadoError()

    servicio_base_existe = db.query(models.ServicioBase).filter(
        models.ServicioBase.id == servicio_base_id,
    ).first()

    if not servicio_base_existe:
        raise exceptions.SucursalServiceNotFoundError()

    validar_disponibilidades(servicio_nuevo.disponibilidades)

    try:
        servicios_existentes = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id == servicio_base_id,
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        if len(servicios_existentes) == 2:
            raise exceptions.SucursalServiceRangosFechasError()

        servicio_actual = servicios_existentes[0]

        if servicio_nuevo.vigente_desde <= servicio_actual.vigente_desde:
            raise exceptions.SucursalServicePosteriorFechaInicioVigenciaError()

        disps_existentes = db.query(models.Disponibilidad).join(models.Servicio).filter(
            models.Servicio.servicio_base_id == servicio_base_id,
        ).order_by(models.Disponibilidad.id.asc()).with_for_update(of=models.Disponibilidad).all()

        # ---------------------------------------------------------
        # 🔎 Detectar superposición
        # ---------------------------------------------------------

        hay_superposicion = (
            servicio_actual.vigente_hasta is None
            or servicio_nuevo.vigente_desde <= servicio_actual.vigente_hasta
        )

        if hay_superposicion:

            # ---------------------------------------------------------
            # 1️⃣ Validar fechas de vigencia y traer turnos desde nueva fecha
            # ---------------------------------------------------------

            turnos_afectados = validar_turnos_vs_nueva_vigencia(
                db,
                servicio_actual.id,
                servicio_nuevo.vigente_hasta,
            )

            # ---------------------------------------------------------
            # 2️⃣ Validar que nuevas disponibilidades cubran esos turnos
            # ---------------------------------------------------------

            validar_turnos_existentes_vs_nueva_config_disps(
                turnos=turnos_afectados,
                disponibilidades_finales=servicio_nuevo.disponibilidades,
            )

            # ---------------------------------------------------------
            # 3️⃣ Cortar servicio actual
            # ---------------------------------------------------------

            servicio_actual.vigente_hasta = servicio_nuevo.vigente_desde - timedelta(days=1)

        servicio = models.Servicio(
            servicio_base_id=servicio_base_id,
            duracion=servicio_nuevo.duracion,
            precio=servicio_nuevo.precio,
            vigente_desde=servicio_nuevo.vigente_desde,
            vigente_hasta=servicio_nuevo.vigente_hasta,
            created_at=timezone.to_naive_utc(timezone.now_utc()),
        )
        db.add(servicio)
        db.flush() # obtiene servicio.id sin commit

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
        
        if hay_superposicion:
            for turno in turnos_afectados:
                turno.servicio_id = servicio.id

        db.commit()
    except Exception:
        db.rollback()
        raise

    servicio_base = db.query(models.ServicioBase).options(
        joinedload(models.ServicioBase.profesional),
        selectinload(models.ServicioBase.servicios).selectinload(models.Servicio.disponibilidades),
        selectinload(models.ServicioBase.excepciones_fechas),
    ).filter_by(id=servicio_base_id, sucursal_id=sucursal_id).first()

    return servicio_base

def update_servicio_version(db: Session, sucursal_id: int, usuario_id: int,
    servicio_base_id: int, servicio_id: int, servicio_update: schemas_sucursal.ServicioUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = servicio_update.model_dump(exclude_unset=True)

    try:
        servicio_base = db.query(models.ServicioBase).filter_by(
            id=servicio_base_id,
            sucursal_id=sucursal_id,
        ).first()

        servicio = db.query(models.Servicio).filter_by(
            id=servicio_id,
            servicio_base_id=servicio_base_id,
        ).with_for_update().first()

        if not servicio_base or not servicio:
            raise exceptions.SucursalServiceNotFoundError()

        # Disponibilidades actuales en DB (las buscamos ahora para bloquear disponibilidades por las dudas en caso
        # de que se cambie la fecha de vigencia vigente_hasta y haya conflicto con un usuario que quiere reservar un turno)
        disps_db = db.query(models.Disponibilidad).filter(
            models.Disponibilidad.servicio_id == servicio_id,
        ).order_by(models.Disponibilidad.id.asc()).with_for_update().all()

        nueva_vigente_hasta = update_data.get("vigente_hasta", servicio.vigente_hasta)

        if nueva_vigente_hasta and nueva_vigente_hasta < servicio.vigente_desde:
            raise RequestValidationError([
                {
                    "type": "value_error",
                    "loc": ("body", "vigente_hasta"),
                    "msg": "La fecha final de la vigencia del servicio debe ser mayor o igual que la fecha de inicio",
                }
            ])
    
        servicio_superpuesto = db.query(models.Servicio).filter(
            models.Servicio.id != servicio_id,
            models.Servicio.servicio_base_id == servicio_base_id,
            # Condición parcial de superposición:
            models.Servicio.vigente_desde <= (nueva_vigente_hasta if nueva_vigente_hasta else date.max),
            or_(
            # esta condición con el modelo de solo modificar vigente_hasta y con solo dos servicios máximo por servicio_base,
            # no es necesario. Sin embargo, podría en el futuro modificarse la lógica y de esta manera ya quedan cubiertos
            # todos los casos de superposición
                models.Servicio.vigente_hasta.is_(None),
                models.Servicio.vigente_hasta >= servicio.vigente_desde,
            ),
        ).first()

        if servicio_superpuesto:
            raise exceptions.SucursalServiceSuperpuestoError()
        
        # Este chequeo es por si el nuevo intervalo de vigencia deja de contemplar algunas fechas y esto se
        # lograría solamente, en este caso, reduciendo la fecha vigente_hasta (recordar que en caso de que la
        # nueva vigente_hasta sea None, significa que la fecha se hace infinita)
        turnos_afectados = validar_turnos_vs_nueva_vigencia(db, servicio_id, nueva_vigente_hasta)

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

            validar_turnos_existentes_vs_nueva_config_disps(
                turnos_afectados,
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
                            servicio_id=servicio_id,
                            dia=disp_json["dia"],
                            hora_inicio=disp_json["hora_inicio"],
                            hora_fin=disp_json["hora_fin"],
                            intervalo=disp_json["intervalo"],
                            cant_turnos_max=disp_json["cant_turnos_max"],
                        )
                    )
        
        servicio.modify_at = timezone.to_naive_utc(timezone.now_utc())
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    servicio = db.query(models.Servicio).options(
        selectinload(models.Servicio.disponibilidades),
    ).filter_by(id=servicio_id).first()

    return servicio

def delete_servicio_version(db: Session, sucursal_id: int, usuario_id: int, servicio_base_id: int, servicio_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalServiceDeletedByEmpleadoError()
    
    try:
        servicio_base = (
            db.query(models.ServicioBase)
            .filter_by(id=servicio_base_id, sucursal_id=sucursal_id)
            .with_for_update()
            .first()
        )

        if not servicio_base:
            raise exceptions.SucursalServiceNotFoundError()

        servicios = (
            db.query(models.Servicio)
            .filter(models.Servicio.servicio_base_id == servicio_base_id)
            .order_by(models.Servicio.id.asc())
            .with_for_update()
            .all()
        )

        servicio = next((s for s in servicios if s.id == servicio_id), None)

        if not servicio:
            raise exceptions.SucursalServiceNotFoundError()

        if len(servicios) == 1:
            raise exceptions.SucursalServiceRangosFechasError()
        
        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id == servicio_id)
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        # Validar que no tenga turnos confirmados
        turno_confirmado = (
            db.query(models.Turno)
            .filter(
                models.Turno.servicio_id == servicio_id,
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.SucursalServiceDeleteWithTurnosConfirmadosError()

        db.delete(servicio) # CASCADE borra disponibilidades
        db.commit()
    except Exception:
        db.rollback()
        raise

def create_excepcion_fecha_servicio(db: Session, sucursal_id: int,
    usuario_id: int, servicio_base_id: int, excepcion_nueva: schemas_sucursal.ExcepcionFechaServicioCreate):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalExceptionDateServiceCreatedByEmpleadoError()
    
    exc_nueva_fecha_inicio = excepcion_nueva.fecha_inicio
    exc_nueva_fecha_fin = excepcion_nueva.fecha_fin

    try:
        servicio_base = (
            db.query(models.ServicioBase)
            .filter_by(id=servicio_base_id, sucursal_id=sucursal_id)
            .with_for_update()
            .first()
        )

        if not servicio_base:
            raise exceptions.SucursalServiceNotFoundError()

        # Lockear todas las excepciones del servicio en orden ascendente
        excepciones = (
            db.query(models.ExcepcionFechaServicio)
            .filter(models.ExcepcionFechaServicio.servicio_base_id == servicio_base_id)
            .order_by(models.ExcepcionFechaServicio.id.asc())
            .with_for_update()
            .all()
        )

        for exc in excepciones:
            if exc.fecha_inicio <= exc_nueva_fecha_fin and exc.fecha_fin >= exc_nueva_fecha_inicio:
                raise exceptions.SucursalExceptionDateServiceSuperpuestaError()

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id == servicio_base_id,
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )
        
        turnos_servicio_base = (
            db.query(models.Turno)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .all()
        )

        for turno in turnos_servicio_base:
            fecha_local = timezone.utc_to_local(turno.fecha_hora).date()

            if exc_nueva_fecha_inicio <= fecha_local <= exc_nueva_fecha_fin:
                raise exceptions.SucursalExceptionDateServiceCreateWithTurnosExistentesError()

        excepcion = models.ExcepcionFechaServicio(
            servicio_base_id=servicio_base_id,
            fecha_inicio=exc_nueva_fecha_inicio,
            fecha_fin=exc_nueva_fecha_fin,
            motivo=excepcion_nueva.motivo,
        )
        db.add(excepcion)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return excepcion

def update_excepcion_fecha_servicio(db: Session, sucursal_id: int, usuario_id: int,
    servicio_base_id: int, excepcion_id: int, excepcion_update: schemas_sucursal.ExcepcionFechaServicioUpdateIn):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalExceptionDateServiceUpdatedByEmpleadoError()
    
    # Convertir a dict solo con campos enviados
    update_data = excepcion_update.model_dump(exclude_unset=True)

    try:
        servicio_base = (
            db.query(models.ServicioBase)
            .filter_by(id=servicio_base_id, sucursal_id=sucursal_id)
            .with_for_update()
            .first()
        )

        if not servicio_base:
            raise exceptions.SucursalServiceNotFoundError()

        # Lockear todas las excepciones del servicio en orden ascendente
        excepciones = (
            db.query(models.ExcepcionFechaServicio)
            .filter(models.ExcepcionFechaServicio.servicio_base_id == servicio_base_id)
            .order_by(models.ExcepcionFechaServicio.id.asc())
            .with_for_update()
            .all()
        )

        excepcion = next(
            (e for e in excepciones if e.id == excepcion_id),
            None
        )

        if not excepcion:
            raise exceptions.SucursalExceptionDateServiceNotFoundError()
        
        exc_nueva_fecha_inicio = update_data.get("fecha_inicio", excepcion.fecha_inicio)
        exc_nueva_fecha_fin = update_data.get("fecha_fin", excepcion.fecha_fin)
        exc_nuevo_motivo = update_data.get("motivo", excepcion.motivo)

        if exc_nueva_fecha_fin < exc_nueva_fecha_inicio:
            if "fecha_inicio" in update_data:
                raise RequestValidationError([
                    {
                        "type": "value_error",
                        "loc": ("body", "fecha_inicio"),
                        "msg": "La fecha final de una excepción de servicio debe ser mayor o igual que la fecha de inicio",
                    }
                ])
            if "fecha_fin" in update_data:
                raise RequestValidationError([
                    {
                        "type": "value_error",
                        "loc": ("body", "fecha_fin"),
                        "msg": "La fecha final de una excepción de servicio debe ser mayor o igual que la fecha de inicio",
                    }
                ])

        for exc in excepciones:
            if exc.id == excepcion_id:
                continue

            if exc_nueva_fecha_inicio <= exc.fecha_fin and exc_nueva_fecha_fin >= exc.fecha_inicio:
                raise exceptions.SucursalExceptionDateServiceSuperpuestaError()

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id == servicio_base_id,
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        turnos_servicio_base = (
            db.query(models.Turno)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .all()
        )

        for turno in turnos_servicio_base:
            fecha_local = timezone.utc_to_local(turno.fecha_hora).date()

            if exc_nueva_fecha_inicio <= fecha_local <= exc_nueva_fecha_fin:
                raise exceptions.SucursalExceptionDateServiceUpdateWithTurnosExistentesError()
        
        # Actualizar campos
        for attr, value in update_data.items():
            setattr(excepcion, attr, value)

        db.commit()
        db.refresh(excepcion)
    except Exception:
        db.rollback()
        raise

    return excepcion

def delete_excepcion_fecha_servicio(db: Session, sucursal_id: int, usuario_id: int, servicio_base_id: int, excepcion_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario, gerente de empresa o gerente de sucursal
    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.SucursalExceptionDateServiceDeletedByEmpleadoError()

    try:
        servicio_base = (
            db.query(models.ServicioBase)
            .filter_by(id=servicio_base_id, sucursal_id=sucursal_id)
            .with_for_update()
            .first()
        )

        if not servicio_base:
            raise exceptions.SucursalServiceNotFoundError()

        excepcion = (
            db.query(models.ExcepcionFechaServicio)
            .filter(
                models.ExcepcionFechaServicio.id == excepcion_id,
                models.ExcepcionFechaServicio.servicio_base_id == servicio_base_id,
            )
            .with_for_update() # no es necesario bloquear pero igual no perjudica en nada
            .first()
        )

        if not excepcion:
            raise exceptions.SucursalExceptionDateServiceNotFoundError()

        db.delete(excepcion)
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_miembros(db: Session, sucursal_id: int, usuario_solicitante_id: int):

    get_sucursal(db, sucursal_id, error_if_not_active=False)

    # Verificar que el usuario solicitante sea gerente de sucursal
    current_user_rol = verificar_rol_en_sucursal(db, usuario_solicitante_id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
        raise exceptions.EmpresaMiembrosViewedByEmpleadoError()

    miembros = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.rol),
    ).filter_by(sucursal_id=sucursal_id).all()

    return miembros

def get_miembro_sucursal(db: Session, sucursal_id: int, usuario_miembro_id: int, lanzar_error: bool = True, bloquear: bool = False):

    query = (
        db.query(models.Miembro_Sucursal)
        .options(
            joinedload(models.Miembro_Sucursal.usuario),
            joinedload(models.Miembro_Sucursal.rol),
        )
        .filter_by(
            usuario_id=usuario_miembro_id,
            sucursal_id=sucursal_id,
        )
    )

    if bloquear:
        query = query.with_for_update(of=models.Miembro_Sucursal)

    miembro_sucursal = query.first()

    if not miembro_sucursal and lanzar_error:
        raise exceptions.SucursalMiembroNotFoundError()

    return miembro_sucursal

# El usuario de la sucursal se borra de esta
def leave_sucursal(db: Session, sucursal_id: int, usuario_id: int):

    get_sucursal(db, sucursal_id)

    verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    try:
        # Traer el objeto de clase Miembro_Sucursal que se eliminará
        miembro_sucursal = get_miembro_sucursal(db, sucursal_id, usuario_id, bloquear=True)

        servicios_base = db.query(models.ServicioBase).filter(
            models.ServicioBase.sucursal_id == sucursal_id,
            models.ServicioBase.profesional_id == usuario_id,
        ).order_by(models.ServicioBase.id.asc()).with_for_update().all()

        ids_servicios_base = [s.id for s in servicios_base]

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(ids_servicios_base),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        turno_confirmado = (
            db.query(models.Turno.id)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.SucursalProfesionalConTurnosConfirmadosOutError()
        
        for servicio_base in servicios_base:
            db.delete(servicio_base) # CASCADE borra servicios versionados (con sus disponibilidades) y excepciones
        
        db.delete(miembro_sucursal)
        db.commit()
    except Exception:
        db.rollback()
        raise

# Solo lo pueden hacer los propietarios o gerentes generales
def add_miembro(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario o gerente de empresa
    verificar_rol_en_empresa(db, usuario_solicitante_id, sucursal.empresa.id)

    try:
        # Traer al menos un objeto de clase Miembro_Sucursal para comprobar que ya está en alguna sucursal al menos
        es_miembro_de_alguna_sucursal = db.query(models.Miembro_Sucursal).join(models.Sucursal).filter(
            models.Miembro_Sucursal.usuario_id == target_id,
            models.Sucursal.empresa_id == sucursal.empresa.id,
        ).order_by(models.Miembro_Sucursal.id.asc()).with_for_update(of=models.Miembro_Sucursal).first()

        if not es_miembro_de_alguna_sucursal:
            raise exceptions.SucursalMiembroAddError()
        
        # Traer el objeto de clase Miembro_Sucursal para ver si ya existe
        miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id, lanzar_error=False)

        if not miembro_sucursal_target:

            db_nuevo_rol_id = auxiliares.get_rol_id(db, nuevo_rol, 'SUCURSAL')
            
            miembro = models.Miembro_Sucursal(
                usuario_id=target_id,
                sucursal_id=sucursal_id,
                rol_id=db_nuevo_rol_id,
            )
            db.add(miembro)

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    miembro_sucursales = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.usuario),
        joinedload(models.Miembro_Sucursal.sucursal),
        joinedload(models.Miembro_Sucursal.rol),
    ).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

    return miembro_sucursales

# Esta función es solo para que un propietario pueda modificar un rol de gerente de sucursal o empleado
# o para que un gerente de empresa pueda modificar un rol de gerente de sucursal o empleado sin que este
# pueda ascender a uno a gerente de empresa o propietario (solo pueden ejecutar esta función los propietarios o gerentes generales)
def update_rol(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str):

    sucursal = get_sucursal(db, sucursal_id)

    # Verificar que el usuario sea propietario o gerente de empresa. Esta función es un recurso global de empresa porque
    # los gerentes de sucursal no pueden modificar empleados ya que significaría que los ascenderían y eso no se puede. Además,
    # los gerentes (de empresa o de sucursal) no pueden modificar a sus pares o superiores. En caso de que se agregue un rol
    # intermedio entre empleado y gerente de sucursal, recién ahí, la función dejaría de ser global y debería hacerse un
    # verificar_rol_en_empresa_o_sucursal además de poner la prohibición de modificación de roles para empleados y este nuevo rol.
    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, sucursal.empresa.id)
    
    roles_empresas = ['PROPIETARIO', 'GERENTE_EMPRESA']
    
    if current_user_rol == 'GERENTE_EMPRESA' and nuevo_rol in roles_empresas:
        raise exceptions.EmpresaRolUpdateError()

    try:
        # Traer el objeto de clase Miembro_Sucursal al que se le modificará el rol
        miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id, bloquear=True)
    
        if nuevo_rol in roles_empresas: # signifca que un gerente de sucursal o empleado pasa a ser gerente de empresa o propietario

            db_nuevo_rol_id = auxiliares.get_rol_id(db, nuevo_rol, 'EMPRESA')

            miembro = models.Miembro_Empresa(
                usuario_id=target_id,
                empresa_id=sucursal.empresa.id,
                rol_id=db_nuevo_rol_id,
            )
            db.add(miembro)
            db.delete(miembro_sucursal_target)
            db.commit()

            miembro = db.query(models.Miembro_Empresa).options(
                joinedload(models.Miembro_Empresa.usuario),
                joinedload(models.Miembro_Empresa.rol),
            ).filter_by(
                usuario_id=target_id,
                empresa_id=sucursal.empresa.id,
            ).first()

            return miembro

        else: # signifca que un gerente de sucursal pasa a ser empleado o viceversa

            db_nuevo_rol_id = auxiliares.get_rol_id(db, nuevo_rol, 'SUCURSAL')

            miembro_sucursal_target.rol_id = db_nuevo_rol_id
            db.commit()

            miembro_sucursales = db.query(models.Miembro_Sucursal).options(
                joinedload(models.Miembro_Sucursal.usuario),
                joinedload(models.Miembro_Sucursal.sucursal),
                joinedload(models.Miembro_Sucursal.rol),
            ).filter(models.Miembro_Sucursal.usuario_id == target_id).all()

            return miembro_sucursales

    except Exception:
        db.rollback()
        raise

def delete_miembro(db: Session, sucursal_id: int, usuario_solicitante_id: int, target_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)

    if usuario_solicitante_id == target_id:
        raise exceptions.SucursalInvalidSelfRemovalError()
    
    try:
        # Traer el objeto de clase Miembro_Sucursal que se eliminará
        miembro_sucursal_target = get_miembro_sucursal(db, sucursal_id, target_id, bloquear=True)

        miembro_sucursal_target_rol = miembro_sucursal_target.rol.nombre

        if not auxiliares.rol_superior(current_user_rol, miembro_sucursal_target_rol):
            raise exceptions.EmpresaMiembroDeleteError()

        servicios_base = db.query(models.ServicioBase).filter(
            models.ServicioBase.sucursal_id == sucursal_id,
            models.ServicioBase.profesional_id == target_id,
        ).order_by(models.ServicioBase.id.asc()).with_for_update().all()

        ids_servicios_base = [s.id for s in servicios_base]

        servicios = db.query(models.Servicio).filter(
            models.Servicio.servicio_base_id.in_(ids_servicios_base),
        ).order_by(models.Servicio.id.asc()).with_for_update().all()

        ids_servicios = [s.id for s in servicios]

        disponibilidades = (
            db.query(models.Disponibilidad)
            .filter(models.Disponibilidad.servicio_id.in_(ids_servicios))
            .order_by(models.Disponibilidad.id.asc())
            .with_for_update()
            .all()
        )

        turno_confirmado = (
            db.query(models.Turno.id)
            .filter(
                models.Turno.servicio_id.in_(ids_servicios),
                models.Turno.estado_turno_sucursal_id == 1,
            )
            .first()
        )

        if turno_confirmado:
            raise exceptions.SucursalMiembroDeleteWithTurnosConfirmadosError()
        
        for servicio_base in servicios_base:
            db.delete(servicio_base) # CASCADE borra servicios versionados (con sus disponibilidades) y excepciones

        db.delete(miembro_sucursal_target)
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_clientes_bloqueados(db: Session, sucursal_id: int, usuario_solicitante_id: int):

    sucursal = get_sucursal(db, sucursal_id, error_if_not_active=False)

    verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)

    bloqueos = db.query(models.BloqueoSucursal).options(
        joinedload(models.BloqueoSucursal.cliente).joinedload(models.Cliente.bloqueo),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(sucursal_id=sucursal_id).all()

    miembros_empresa = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.rol),
    ).filter_by(empresa_id=sucursal.empresa.id).all()

    miembros_sucursal = db.query(models.Miembro_Sucursal).options(
        joinedload(models.Miembro_Sucursal.rol),
    ).filter_by(sucursal_id=sucursal_id).all()

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
            miembro_rol = m.rol.nombre

        elif b.created_by_id in miembros_sucursal_map:
            m = miembros_sucursal_map[b.created_by_id]
            miembro_rol = m.rol.nombre

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
        joinedload(models.BloqueoSucursal.cliente).joinedload(models.Cliente.bloqueo),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(sucursal_id=sucursal_id, cliente_id=cliente_id).first()

    if bloqueo:
        return bloqueo, current_user_rol

    try:
        nuevo_bloqueo = models.BloqueoSucursal(
            sucursal_id=sucursal_id,
            cliente_id=cliente_id,
            created_by_id=usuario_solicitante_id,
            motivo=motivo,
            created_at=timezone.to_naive_utc(timezone.now_utc()),
        )
        db.add(nuevo_bloqueo)
        db.commit()
    except Exception:
        db.rollback()
        raise

    bloqueo = db.query(models.BloqueoSucursal).options(
        joinedload(models.BloqueoSucursal.cliente).joinedload(models.Cliente.bloqueo),
        joinedload(models.BloqueoSucursal.usuario_bloqueador),
    ).filter_by(id=nuevo_bloqueo.id).first()
    
    return bloqueo, current_user_rol

def unlock_cliente(db: Session, sucursal_id: int, usuario_solicitante_id: int, cliente_id: int):

    sucursal = get_sucursal(db, sucursal_id)

    current_user_rol = verificar_rol_en_empresa_o_sucursal(db, usuario_solicitante_id, sucursal.empresa.id, sucursal_id)
    if current_user_rol == 'EMPLEADO':
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

'''
Así se pediría, por ejemplo, en la solicitud HTTP:
GET /sucursales/5/notificaciones?leidas=false&id_ultimo=1234&limit=20
'''
def get_notificaciones(
    db: Session,
    sucursal_id: int,
    usuario_id: int,
    leidas: bool | None = None,
    id_ultimo: int | None = None,
    limit: int = 20,
):
    '''
    Devuelve las notificaciones de una sucursal con paginación.
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
    get_sucursal(db, sucursal_id)

    verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    query = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.sucursal_id == sucursal_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
    )

    # Aplicar paginación por cursor si se envió id_ultimo
    if id_ultimo:
        query = query.filter(
            models.Notificacion.id < id_ultimo,
        )
    
    # Filtro por leidas (IMPORTANTE usar is not None)
    if leidas is not None:
        query = query.filter(
            models.Notificacion.leida == leidas,
        )

    query = query.order_by(models.Notificacion.id.desc())

    limit = min(limit, 100) # no más de 100 por consulta

    # notificaciones es una lista de objetos de clase Notificacion de SQLAlchemy
    notificaciones = query.limit(limit).all()

    ultimo_cursor_id = notificaciones[-1].id if notificaciones else None

    return notificaciones, ultimo_cursor_id

def get_notificaciones_nuevas(db: Session, sucursal_id: int, usuario_id: int, id_posterior: int):

    get_sucursal(db, sucursal_id)
    
    verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    notificaciones_nuevas = db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id,
        models.Notificacion.sucursal_id == sucursal_id,
        models.Notificacion.fecha_hora_minima_de_envio <= timezone.to_naive_utc(timezone.now_utc()),
        models.Notificacion.id > id_posterior,
    ).order_by(models.Notificacion.id.desc()).all()

    return notificaciones_nuevas

def update_notificacion_leida(db: Session, sucursal_id: int, usuario_id: int, notificacion_id: int):

    get_sucursal(db, sucursal_id)
    
    verificar_rol_en_sucursal(db, usuario_id, sucursal_id)

    try:
        filas = db.query(models.Notificacion).filter(
            models.Notificacion.id == notificacion_id,
            models.Notificacion.usuario_id == usuario_id, # chequeo que el mismo usuario de la notificación sea el que hace la request
            models.Notificacion.sucursal_id == sucursal_id, # chequeo adicional de la sucursal
        ).update(
            {"leida": True},
            synchronize_session=False
        )

        if filas == 0:
            raise exceptions.NotificationNotFoundError()

        db.commit()
    except Exception:
        db.rollback()
        raise

def validar_turnos_vs_nueva_vigencia(
    db: Session,
    servicio_id: int,
    nueva_fecha_hasta: date | None,
):

    turnos = db.query(models.Turno).filter(
        models.Turno.servicio_id == servicio_id,
        models.Turno.estado_turno_sucursal_id == 1,
        models.Turno.eliminado_por_sucursal == False,
    ).all()

    fuera_de_rango = 0
    turnos_dentro_del_nuevo_rango = []

    for turno in turnos:
        fecha_local = timezone.utc_to_local(turno.fecha_hora).date()

        if nueva_fecha_hasta and fecha_local > nueva_fecha_hasta:
            fuera_de_rango += 1
            continue
        
        turnos_dentro_del_nuevo_rango.append(turno)

    if fuera_de_rango > 0:
        raise exceptions.SucursalServiceUpdateVigenciaWithTurnosExistentesError(
            cant_turnos_actual=fuera_de_rango,
        )
    
    return turnos_dentro_del_nuevo_rango # los que estaban en el viejo rango y ahora quedarán en el nuevo rango

def validar_turnos_existentes_vs_nueva_config_disps(
    turnos = list[models.Turno],
    disponibilidades_finales: list,
):
    """
    Verifica que los turnos confirmados del servicio sigan siendo válidos con la nueva configuración de disponibilidades.
    disponibiliades_finales será cualquier lista de objetos a los que se pueda acceeder a sus campos o atributos con .atributo,
    como, por ejemplo, una lista de objetos models.Disponibilidad con objetos schemas_common.DisponibilidadServicio
    """

    # Agrupar por fecha_hora exacta
    turnos_por_fecha_hora = defaultdict(list)
    for t in turnos:
        turnos_por_fecha_hora[t.fecha_hora].append(t)

    # Validar cada fecha_hora existente
    for fecha_hora, lista_turnos in turnos_por_fecha_hora.items():

        cant_turnos_actual = len(lista_turnos)

        disponibilidad_que_cubre = None

        for d in disponibilidades_finales:
            if disponibilidad_cubre_turno(d, fecha_hora):
                disponibilidad_que_cubre = d
                break

        if disponibilidad_que_cubre is None:
            cant_turnos_max = 0
        else:
            cant_turnos_max = disponibilidad_que_cubre.cant_turnos_max
        
        dia, hora = timezone.extraer_dia_y_hora_en_local(fecha_hora)

        if cant_turnos_actual > cant_turnos_max and disponibilidad_que_cubre is not None:
            raise exceptions.SucursalServiceUpdateDisponibilidadWithTurnosExistentesError(
                dia=constantes.DIAS_NOMBRES[dia],
                hora=hora,
                cant_turnos_max=cant_turnos_max,
                cant_turnos_actual=cant_turnos_actual,
                fecha=timezone.utc_to_local(fecha_hora).date(),
            )
        if cant_turnos_actual > cant_turnos_max and disponibilidad_que_cubre is None:
            raise exceptions.SucursalServiceDeleteDisponibilidadWithTurnosExistentesError(
                dia=constantes.DIAS_NOMBRES[dia],
                hora=hora,
                cant_turnos_actual=cant_turnos_actual,
                fecha=timezone.utc_to_local(fecha_hora).date(),
            )