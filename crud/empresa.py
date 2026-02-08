from datetime import datetime, timedelta

from fastapi import UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload
import cloudinary.uploader

from crud.common import get_empresa, verificar_rol_en_empresa, nuevo_estado_check
from core import models, constantes, exceptions, auxiliares, mensajes, timezone
from schemas import common as schemas_common
from schemas import empresa as schemas_empresa

# Crear empresa
def create_empresa(db: Session, empresa: schemas_empresa.EmpresaCreate):

    empresa_existe = db.query(models.Empresa).filter_by(email=empresa.email).first()
    if empresa_existe:
        return empresa_existe
    
    # Crear el objeto de empresa
    db_empresa = models.Empresa(
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        email_verificado=False,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2)

    db.add(db_empresa)
    db.flush()

    # Agregar teléfonos
    for t in empresa.telefonos:
        db_tel = models.Telefono(numero=t.numero, empresa_id=db_empresa.id)
        db.add(db_tel)

    # Agregar dirección
    db_dir = models.Direccion(
        empresa_id=db_empresa.id,
        calle=empresa.direccion.calle,
        altura=empresa.direccion.altura,
        localidad=empresa.direccion.localidad,
        departamento=empresa.direccion.departamento,
        provincia=empresa.direccion.provincia,
        pais=empresa.direccion.pais,
        lat=empresa.direccion.lat,
        lng=empresa.direccion.lng,
        aclaracion=empresa.direccion.aclaracion)

    db.add(db_dir)

    return db_empresa

def asignar_rol_de_propietario(db: Session, usuario_id: int, empresa_id: int):
    
    db_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol=1)
    db.add(db_miembro)

def update(db: Session, empresa_id: int, usuario_id: int, empresa_update: schemas_empresa.EmpresaUpdateIn):

    db_emp = get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaUpdateByEmpleadoError()
    
    try:
        # ----------------------------
        # 1️⃣ Actualizar campos simples
        # ----------------------------
        for attr, value in empresa_update.dict(exclude_unset=True).items():
            if attr not in ["telefonos", "direccion"]:
                setattr(db_emp, attr, value)

        # ----------------------------
        # 2️⃣ Actualizar TELÉFONOS
        # ----------------------------
        if empresa_update.telefonos is not None:
            current_phones = {t.id: t for t in db_emp.telefonos}
            new_ids = set()

            for tel in empresa_update.telefonos: # tel es un objeto de la clase schema TelefonoConID

                if tel.id and tel.id in current_phones:
                    # Actualizar teléfono existente
                    db_tel = current_phones[tel.id]
                    db_tel.numero = tel.numero
                    new_ids.add(tel.id)
                else:
                    # Crear nuevo teléfono
                    new_tel = models.Telefono(numero=tel.numero, empresa_id=empresa_id)
                    db.add(new_tel)

            # Eliminar teléfonos que ya no están en la lista
            for old_id in list(current_phones.keys()):
                if old_id not in new_ids:
                    db.delete(current_phones[old_id])

        # ----------------------------
        # 3️⃣ Actualizar DIRECCIÓN
        # ----------------------------
        if empresa_update.direccion is not None:
            d = empresa_update.direccion
            if db_emp.direccion:
                db_dir = db_emp.direccion
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
                    db.delete(db_emp.direccion)
                    new_dir = models.Direccion(
                        empresa_id=empresa_id,
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
                    empresa_id=empresa_id,
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

        db.commit()

    except Exception:
        db.rollback()
        raise
    
    empresa = get_empresa(db, empresa_id)

    return empresa, current_user_rol

def update_logo(db: Session, empresa_id: int, file: UploadFile | None):

    empresa = get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaUpdateByEmpleadoError()
    
    # Si no mandan archivo, borrar
    if file is None:
        if empresa.logo_public_id:
            cloudinary.uploader.destroy(empresa.logo_public_id)

        logo_url = None
        logo_public_id = None

    else:
        if not file.content_type.startswith("image/"):
            raise exceptions.LogoInvalidError(field="logo")

        content = file.file.read()
        
        auxiliares.validar_logo(content) # valido el logo

        # Creo el Public ID fijo por empresa
        public_id = f"empresa_{empresa.id}_logo"

        # Subir (overwrite)
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            overwrite=True,
            resource_type="image"
        )

        logo_url = result["secure_url"]
        logo_public_id = result["public_id"]

    try:
        empresa.logo_url = logo_url
        empresa.logo_public_id = logo_public_id
        db.commit()
        db.refresh(empresa)
    except Exception:
        db.rollback()
        raise
    
    return empresa.logo_url

def acceder(db: Session, empresa_id: int, usuario_id: int):

    empresa = get_empresa(db, empresa_id)
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)

    return empresa, current_user_rol

def get_turnos(db: Session, empresa_id: int, usuario_id: int):
    '''
    Devuelve todos los turnos de una empresa que aparecen en la tabla turno: los futuros y los pasados que la empresa no eliminó.
    Van ordenados del más antiguo al más lejano (fecha descendente).
    '''

    get_empresa(db, empresa_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    query = db.query(models.Turno).filter(models.Turno.empresa_id == empresa_id,
                                              or_(models.Turno.eliminado == None, models.Turno.eliminado == 'u'))  # Debe ser NULL o 'u'

    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Turno
    query = query.options(
        joinedload(models.Turno.usuario), # Usuario relacionado
        joinedload(models.Turno.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Turno.estado_turno_empresa) # Estado del turno de la empresa
    )
    
    # Los que tienen fecha más antigua aparecerán más arriba que los de fecha más futura en el tiempo
    turnos = query.order_by(models.Turno.fecha_hora.asc()).all()

    return turnos # turnos es una lista de objetos de clase Turno de SQLAlchemy

def get_turno(db: Session, turno_id: int):

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.estado_turno_empresa)).filter(models.Turno.id == turno_id).first()
    
    return turno

def update_turno(db: Session, empresa_id: int, user: models.Usuario, turno_update: schemas_common.TurnoUpdateIn):

    get_empresa(db, empresa_id)
    current_user_rol = verificar_rol_en_empresa(db, user.id, empresa_id)

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.empresa)).filter_by(id=turno_update.id, empresa_id=empresa_id).first()
    if not turno:
        raise exceptions.TurnoNotFoundError()
    
    servicio = db.query(models.Servicio).filter_by(id=turno.servicio_id).first()
    if not servicio:
        raise EmpresaServiceNotFoundError()
    
    nuevo_estado = turno_update.estado_turno
    inicio_turno = timezone.ensure_utc(turno.fecha_hora) # convertimos de naive UTC a aware UTC
    email_cancelacion = False

    # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno para luego ponerlo en el turno
    estado_obj = db.query(models.Estado_Turno).filter(
        models.Estado_Turno.estado.ilike(nuevo_estado)).first()
    
    nuevo_estado_check(db, nuevo_estado, inicio_turno, turno.duracion, cancelado_por_usuario=False)

    if turno.estado_turno_empresa_id != 1: # si no es CONFIRMADO el estado
        raise exceptions.TurnoUpdateStateImmutableError()
    
    if (nuevo_estado == 'CANCELADO_POR_EMPRESA'
        and turno.profesional_id != 1 # si tiene profesional
        and turno.profesional_id != user.id
        and servicio.cancelacion_limitada):

            profesional_rol = verificar_rol_en_empresa(db, turno.profesional_id, empresa_id)

            if not auxiliares.rol_superior(current_user_rol, profesional_rol):
                raise exceptions.TurnoCancelByMiembroForbiddenError()

    try:
        turno.estado_turno_empresa_id = estado_obj.id

        if nuevo_estado == 'CANCELADO_POR_EMPRESA':
            turno.estado_turno_usuario_id = estado_obj.id
            email_cancelacion = True

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    if email_cancelacion:
        try:
            mensajes.send_turno_cancelado_email(
                to_email=turno.usuario.email,
                us_emp_nombre=turno.empresa.nombre,
                fecha_hora=inicio_turno,
                servicio=turno.nombre_de_servicio,
                motivo=turno_update.motivo)
        except exceptions.EmailSendFailedError():
            pass

    # Precargar relaciones importantes antes de devolver
    turno = get_turno(db, turno.id)

    return turno

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
def delete_turno(db: Session, empresa_id: int, usuario_id: int, turno_id: int, lista_estados: list):

    get_empresa(db, empresa_id)
    verificar_rol_en_empresa(db, usuario_id, empresa_id)
    
    turno = get_turno(db, turno_id)

    if not turno:
        raise exceptions.TurnoNotFoundError()

    # Esto me va a asegurar que el usuario o empresa tenga que cambiarle el estado a uno de los 
    # posibles para poder mover el turno a la tabla Historial y no que lo mueva sin haber cambiado 
    # el estado previamente y de esta manera, el historial quede con los estados bien puestos
    # (por seguridad si la petición de eliminación llega antes que la de cambio de estado)
    if turno.estado_turno_empresa.estado not in lista_estados:
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
                estado_turno_usuario_id=None,
                estado_turno_empresa_id=turno.estado_turno_empresa_id)

            turno.eliminado = 's' # turno eliminado por la sucursal
        
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

            # Significa que el turno ya fue movido por el usuario a la tabla Historial y solo queda 
            # agarrar el estado en estado_turno_empresa_id del turno de la tabla Turno (es un número entero)
            # y ponerlo en el atributo estado_turno_empresa_id del turno de la tabla Historial.
            e = turno.estado_turno_empresa_id
            turno_en_historial.estado_turno_empresa_id = e

            db.delete(turno)

        db.commit()
    except Exception:
        db.rollback()
        raise

def get_estados_turnos(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)
    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    turnos = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_empresa)).filter_by(empresa_id=empresa_id).all()
    
    return turnos

# Devuelve todos los turnos que la empresa ya completó
'Así se pediría, por ejemplo, en la solicitud HTTP: GET /empresas/5/historial?before=2025-10-10T00:00:00Z'
def get_historial(db: Session, empresa_id: int, usuario_id: int, fecha_hora_ultima: datetime, limit=20):
    '''
    Devuelve el historial de turnos de una empresa con paginación.
    Van ordenados del más reciente al más antiguo (fecha ascendente).
    '''
    get_empresa(db, empresa_id)

    # Verificar que el usuario solicitante sea miembro de la empresa
    verificar_rol_en_empresa(db, usuario_id, empresa_id)

    query = db.query(models.Historial).filter(models.Historial.empresa_id == empresa_id)

    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Historial
    query = query.options(
        joinedload(models.Historial.usuario), # Usuario relacionado
        joinedload(models.Historial.profesional), # Usuario relacionado (como profesional)
        joinedload(models.Historial.estado_turno_empresa) # Estado del turno de la empresa
    )

    fecha_hora_ultima = timezone.to_naive_utc(fecha_hora_ultima) # garantía defensiva

    query = query.order_by(models.Historial.fecha_hora.desc())
    query = query.filter(models.Historial.fecha_hora < fecha_hora_ultima)

    # historial es una lista de objetos de clase Historial de SQLAlchemy
    historial = query.limit(limit).all()

    # ultimo_cursor es el atributo fecha_hora del último turno en la lista historial (el más antiguo de los devueltos), por lo que su tipo es datetime
    ultimo_cursor = historial[-1].fecha_hora if historial else None 

    return historial, ultimo_cursor

def get_servicios(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)

    # Verificar que el usuario solicitante sea propietario o gerente
    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceViewByEmpleadoError()

    servicios = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades) # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(empresa_id=empresa_id).all()

    return servicios

def create_servicio(db: Session, empresa_id: int, usuario_id: int, servicio_nuevo: schemas_empresa.ServicioCreate):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceCreateByEmpleadoError()
    
    profesional_id = servicio_nuevo.profesional_id
    if profesional_id is None:
        profesional_id = 1
    
    if profesional_id != 1:
        verificar_rol_en_empresa(db, profesional_id, empresa_id)

    # Chequeo si ya existe un servicio igual en la empresa con el mismo nombre y profesional (tenga o no)
    servicio = db.query(models.Servicio).filter_by(
        empresa_id=empresa_id,
        nombre=servicio_nuevo.nombre,
        profesional_id=profesional_id).first()
    if servicio:
        raise exceptions.EmpresaServiceDuplicatedError()

    try:
        # Crear servicio
        servicio = models.Servicio(
            empresa_id=empresa_id,
            nombre=servicio_nuevo.nombre,
            duracion=servicio_nuevo.duracion,
            precio=servicio_nuevo.precio,
            aclaracion=servicio_nuevo.aclaracion,
            profesional_id=profesional_id,
            minutos_min_reserva=servicio_nuevo.minutos_min_reserva,
            dias_max_reserva=servicio_nuevo.dias_max_reserva,
            cancelacion_limitada=servicio_nuevo.cancelacion_limitada)
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
                    cant_turnos_max=cant_max)
                db.add(disp)

        db.commit()
    except Exception:
        db.rollback()
        raise

    servicio = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades) # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(id=servicio.id, empresa_id=empresa_id).first()

    return servicio

def update_servicio(db: Session, empresa_id: int, usuario_id: int, servicio_update: schemas_empresa.ServicioUpdateIn):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceUpdateByEmpleadoError()
    
    # Traer servicio a actualizar
    servicio = db.query(models.Servicio).filter_by(id=servicio_update.id, empresa_id=empresa_id).first()
    if not servicio:
        raise exceptions.EmpresaServiceNotFoundError()
    
    # Convertir a dict solo con campos enviados
    update_data = servicio_update.dict(exclude_unset=True)

    # Chequeo si ya existe otro servicio en la empresa con el mismo nombre y profesional (tenga o no)
    nombre_nuevo = update_data.get("nombre", servicio.nombre) # Si no vino, uso el nombre que ya estaba
    profesional_id_nuevo = update_data.get("profesional_id", servicio.profesional_id) # Si no vino, uso el profesional_id que ya estaba

    if profesional_id_nuevo is None:
        profesional_id_nuevo = 1
    
    if profesional_id_nuevo != 1:
        verificar_rol_en_empresa(db, profesional_id_nuevo, empresa_id)

    existe_servicio = db.query(models.Servicio).filter(
        models.Servicio.id != servicio_update.id,
        models.Servicio.empresa_id == empresa_id,
        models.Servicio.nombre == nombre_nuevo,
        models.Servicio.profesional_id == profesional_id_nuevo).first()
    
    if existe_servicio:
        raise exceptions.EmpresaServiceDuplicatedError()
    
    try:

        # Actualizar campos simples (excepto disponibilidades)
        for attr, value in update_data.items():
            if attr == "disponibilidades":
                continue
            if attr == "profesional_id" and value is None:
                value = 1
            setattr(servicio, attr, value)  # Si value es None, se actualiza; si no existe en dict, se ignora

        if "disponibilidades" in update_data:

            def disp_key(d):
                return (
                    d.dia,
                    d.hora_inicio,
                    d.hora_fin,
                    d.intervalo,
                    d.cant_turnos_max
                )

            # Disponibilidades actuales en BD
            disps_db = db.query(models.Disponibilidad).filter(models.Disponibilidad.servicio_id == servicio.id).all()

            db_map = {disp_key(d): d for d in disps_db}

            # Disponibilidades del JSON
            json_map = {}
            for d in update_data["disponibilidades"]:
                key = (
                    d["dia"],
                    d["hora_inicio"],
                    d["hora_fin"],
                    d["intervalo"],
                    d["cant_turnos_max"]
                )
                json_map[key] = d

            # Borrar las que ya no están
            for key, disp_db in db_map.items():
                if key not in json_map:
                    db.delete(disp_db)

            # Agregar las nuevas
            for key, disp_json in json_map.items():
                if key not in db_map:
                    db.add(models.Disponibilidad(
                        servicio_id=servicio.id,
                        dia=disp_json["dia"],
                        hora_inicio=disp_json["hora_inicio"],
                        hora_fin=disp_json["hora_fin"],
                        intervalo=disp_json["intervalo"],
                        cant_turnos_max=disp_json["cant_turnos_max"]
                    ))

        db.commit()
    except Exception:
        db.rollback()
        raise
    
    servicio = db.query(models.Servicio).options(
        joinedload(models.Servicio.profesional), # Para cada Servicio que se cargó, trae el Usuario asociado
        selectinload(models.Servicio.disponibilidades) # Para cada Servicio que se cargó, trae todas las filas de Disponibilidad
    ).filter_by(id=servicio.id, empresa_id=empresa_id).first()

    return servicio

def delete_servicios(db: Session, empresa_id: int, usuario_id: int, servicios_delete: list[int]):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaServiceDeleteByEmpleadoError()
    
    try:
        # Iterar sobre los IDs de servicios a eliminar
        for servicio_id in servicios_delete:
            # Traer servicio a eliminar
            servicio = db.query(models.Servicio).filter_by(id=servicio_id, empresa_id=empresa_id).first()
            if not servicio:
                raise exceptions.EmpresaServiceNotFoundError()

            # Eliminar servicio
            db.delete(servicio) # CASCADE borra disponibilidades

        db.commit()
    except Exception:
        db.rollback()
        raise

def get_miembros(db: Session, empresa_id: int, usuario_solicitante_id: int):

    get_empresa(db, empresa_id)

    # Verificar que el usuario solicitante sea propietario o gerente
    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaMiembrosViewByEmpleadoError()

    miembros = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario)).filter_by(empresa_id=empresa_id).all()

    return miembros

def get_miembro(db: Session, empresa_id: int, usuario_miembro_id: int):

    miembro_empresa = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario)).filter_by(
        usuario_id=usuario_miembro_id, empresa_id=empresa_id).first()

    if not miembro_empresa:
        raise exceptions.EmpresaMiembroNotFoundError()

    return miembro_empresa

def contar_propietarios(db: Session, empresa_id: int):

    cant = db.query(models.Miembro_Empresa).filter(
        models.Miembro_Empresa.empresa_id == empresa_id,
        models.Miembro_Empresa.rol == 1).count()

    return cant

def update_rol(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int, nuevo_rol: str):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    if current_user_rol != 'propietario':
        raise exceptions.EmpresaRolUpdateError()
    
    # Traer el objeto de clase Miembro_Empresa al que se le modificará el rol
    miembro_empresa_target = get_miembro(db, empresa_id, target_id)

    miembro_empresa_target_rol = constantes.Rol(miembro_empresa_target.rol).name
    
    if usuario_solicitante_id == target_id: # se modifica él mismo

        if nuevo_rol == 'propietario':
            return 'propietario' # no tiene sentido modificarlo ya que es el mismo propietario cambiándose a propietario

        propietarios = contar_propietarios(db, empresa_id)
        if propietarios <= 1 and nuevo_rol != 'propietario':
            raise exceptions.EmpresaPropietarioOutError()

    else: # modifica a otro miembro

        if miembro_empresa_target_rol == 'propietario':
            raise exceptions.EmpresaRolPropietarioUpdateError()

    db_nuevo_rol = constantes.Rol[nuevo_rol].value
    
    try:
        miembro_empresa_target.rol = db_nuevo_rol
        db.commit()
        db.refresh(miembro_empresa_target)
    except Exception:
        db.rollback()
        raise
    
    return constantes.Rol(miembro_empresa_target.rol).name

# El usuario de la empresa se borra de esta
def empresa_out(db: Session, empresa_id: int, usuario_id: int):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_id, empresa_id)

    # Traer el objeto de clase Miembro_Empresa que se eliminará
    miembro_empresa = get_miembro(db, empresa_id, usuario_id)

    miembro_empresa_rol = constantes.Rol(miembro_empresa.rol).name

    if miembro_empresa_rol == "propietario":
        propietarios = contar_propietarios(db, empresa_id)
        if propietarios <= 1:
            raise exceptions.EmpresaPropietarioOutError()
    
    try:
        servicios = db.query(models.Servicio).filter(
            models.Servicio.empresa_id == empresa_id,
            models.Servicio.profesional_id == usuario_id).all()

        for servicio in servicios:
            db.delete(servicio)
        
        db.delete(miembro_empresa)
        db.commit()
    except Exception:
        db.rollback()
        raise

def delete_miembro(db: Session, empresa_id: int, usuario_solicitante_id: int, target_id: int):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    if usuario_solicitante_id == target_id:
        raise exceptions.EmpresaInvalidSelfRemovalError()

    # Traer el objeto de clase Miembro_Empresa que se eliminará
    miembro_empresa_target = get_miembro(db, empresa_id, target_id)

    miembro_empresa_target_rol = constantes.Rol(miembro_empresa_target.rol).name
    
    roles_superiores = ["propietario", "gerente"]

    if miembro_empresa_target_rol == 'propietario':
        raise exceptions.EmpresaMiembroPropietarioDeleteError()
    if current_user_rol == 'gerente' and miembro_empresa_target_rol in roles_superiores:
        raise exceptions.EmpresaMiembroDeleteByGerenteError()
    if current_user_rol == 'empleado':
       raise exceptions.EmpresaMiembroDeleteByEmpleadoError()
    
    servicios = db.query(models.Servicio).filter(
        models.Servicio.empresa_id == empresa_id,
        models.Servicio.profesional_id == target_id).all()

    try:
        for servicio in servicios:
            db.delete(servicio)
        
        db.delete(miembro_empresa_target)
        db.commit()
    except Exception:
        db.rollback()
        raise

def get_usuarios_bloqueados(db: Session, empresa_id: int, usuario_solicitante_id: int):

    get_empresa(db, empresa_id)

    verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    bloqueos = db.query(models.Empresa_Bloqueo).options(
        joinedload(models.Empresa_Bloqueo.usuario),
        joinedload(models.Empresa_Bloqueo.usuario_bloqueador)).filter_by(empresa_id=empresa_id).all()

    miembros = db.query(models.Miembro_Empresa).filter_by(empresa_id=empresa_id).all()

    resultados = []

    for b in bloqueos:
        miembro_rol = None
        for m in miembros:
            if m.usuario_id == b.created_by_id:
                miembro_rol = constantes.Rol(m.rol).name
                break

        resultados.append((b, miembro_rol))

    return resultados

def block_usuario(db: Session, empresa_id: int, usuario_solicitante_id: int, target_email: str, motivo: str | None):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)

    usuario_target = db.query(models.Usuario).filter_by(email=target_email).first()
    if not usuario_target:
        raise exceptions.UserNotFoundError()

    # Chequeo que no sea miembro de la empresa el usuario a bloquear
    miembro_empresa = db.query(models.Miembro_Empresa).filter_by(
        usuario_id=usuario_target.id, empresa_id=empresa_id).first()

    if miembro_empresa:
        raise exceptions.EmpresaBlockMiembroError()

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    try:
        nuevo_bloqueo = models.Empresa_Bloqueo(empresa_id=empresa_id,
            usuario_id=usuario_target.id, created_by_id=usuario_solicitante_id, motivo=motivo, created_at=ahora_utc)
        db.add(nuevo_bloqueo)
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    bloqueo = db.query(models.Empresa_Bloqueo).options(
        joinedload(models.Empresa_Bloqueo.usuario),
        joinedload(models.Empresa_Bloqueo.usuario_bloqueador)).filter_by(id=nuevo_bloqueo.id).first()
    
    return bloqueo, current_user_rol

def unlock_usuario(db: Session, empresa_id: int, usuario_solicitante_id: int, target_email: str):

    get_empresa(db, empresa_id)

    current_user_rol = verificar_rol_en_empresa(db, usuario_solicitante_id, empresa_id)
    if current_user_rol == 'empleado':
        raise exceptions.EmpresaUnlockUserByEmpleadoError()

    usuario_target = db.query(models.Usuario).filter_by(email=target_email).first()
    if not usuario_target:
        raise exceptions.UserNotFoundError()
    
    bloqueo = db.query(models.Empresa_Bloqueo).filter_by(empresa_id=empresa_id, usuario_id=usuario_target.id).first()
    if not bloqueo:
        return # si no estaba bloqueado, se responde con éxito igual
    
    try:
        db.delete(bloqueo)
        db.commit()
    except Exception:
        db.rollback()
        raise