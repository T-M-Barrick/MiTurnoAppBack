import random
from datetime import date, time, datetime, timedelta

from fastapi import HTTPException, Depends, Cookie
from jose import JWTError, jwt
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from passlib.context import CryptContext

from core import models, schemas, autenticacion, auxiliares, variables
from core.database import get_db

# ------------------ CRUD USUARIOS Y EMPRESAS ------------------ #

# Devuelve todos los turnos que el usuario o empresa ya completó
'Así se pediría, por ejemplo, en la solicitud HTTP: GET /usuarios/5/historial?before=2025-10-10T00:00:00'
def get_historial_turnos(db: Session, u_e_id: int, fecha_hora_ultima: datetime, user=True, limit=20):
    '''
    Devuelve el historial de turnos de un usuario o empresa con paginación.
    Van ordenados del más reciente al más antiguo (fecha ascendente).
    '''
    if user:
        query = db.query(models.Historial).filter(models.Historial.usuario_id == u_e_id)
    else:
        query = db.query(models.Historial).filter(models.Historial.empresa_id == u_e_id)

    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Historial
    query = query.options(
        joinedload(models.Historial.usuario), # Usuario relacionado
        joinedload(models.Historial.empresa), # Empresa relacionada
        joinedload(models.Historial.estado_turno_usuario), # Estado del turno del usuario
        joinedload(models.Historial.estado_turno_empresa) # Estado del turno de la empresa
    )

    query = query.order_by(models.Historial.fecha_hora.desc())
    query = query.filter(models.Historial.fecha_hora < fecha_hora_ultima)

    # historial es una lista de objetos de clase Historial de SQLAlchemy
    historial = query.limit(limit).all()

    # ultimo_cursor es el atributo fecha_hora del último turno en la lista historial (el más antiguo de los devueltos), por lo que su tipo es datetime
    ultimo_cursor = historial[-1].fecha_hora if historial else None 

    return historial, ultimo_cursor

def get_turnos(db: Session, u_e_id: int, user=True):
    '''
    Devuelve todos los turnos de un usuario o empresa que aparecen en la tabla turno: los futuros y los pasados que el usuario o empresa no eliminó.
    Van ordenados del más antiguo al más lejano (fecha descendente).
    '''
    if user:
        query = db.query(models.Turno).filter(models.Turno.usuario_id == u_e_id,
                                              or_(models.Turno.eliminado == None, models.Turno.eliminado == 'e'))  # Debe ser NULL o 'e'
    else:
        query = db.query(models.Turno).filter(models.Turno.empresa_id == u_e_id,
                                              or_(models.Turno.eliminado == None, models.Turno.eliminado == 'u'))  # Debe ser NULL o 'u'
    
    # Traigo relaciones con los atributos definidos en la parte de relationship de la tabla Turno
    query = query.options(
        joinedload(models.Turno.usuario), # Usuario relacionado
        joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion), # Empresa relacionada
        joinedload(models.Turno.estado_turno_usuario), # Estado del turno del usuario
        joinedload(models.Turno.estado_turno_empresa) # Estado del turno de la empresa
    )
    
    # Los que tienen fecha más antigua aparecerán más arriba que los de fecha más futura en el tiempo
    turnos = query.order_by(models.Turno.fecha_hora.asc()).all()

    return turnos # turnos es una lista de objetos de clase Turno de SQLAlchemy

def modificar_turno(db: Session, turno: models.Turno, nuevo_estado: str, user=True):

    if user:
        # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno_Usuario para luego ponerlo en el turno
        estado_obj = db.query(models.Estado_Turno_Usuario).filter(models.Estado_Turno_Usuario.estado.ilike(nuevo_estado)).first()
        if estado_obj:
            # Modificar solo el estado del turno
            turno.estado_turno_usuario_id = estado_obj.id
    else:
        # Busco el id que corresponde al estado nuevo_estado de la tabla Estado_Turno_Empresa para luego ponerlo en el turno
        estado_obj = db.query(models.Estado_Turno_Empresa).filter(models.Estado_Turno_Empresa.estado.ilike(nuevo_estado)).first()
        if estado_obj:
            # Modificar solo el estado del turno
            turno.estado_turno_empresa_id = estado_obj.id
    if not estado_obj:
        raise ValueError(f"Estado inválido: {nuevo_estado}")

    # Guardar cambios
    db.commit()

    # Precargar relaciones importantes antes de devolver
    turno = db.query(models.Turno).options(
            joinedload(models.Turno.usuario),
            joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion),
            joinedload(models.Turno.estado_turno_usuario),
            joinedload(models.Turno.estado_turno_empresa)).filter(models.Turno.id == turno.id).first()

    return turno

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
def agregar_turno_historial(db: Session, turno: models.Turno, lista_estados, user=True):

    # Esto me va a asegurar que el usuario o empresa tenga que cambiarle el estado a uno de los 
    # posibles para poder mover el turno a la tabla Historial y no que lo mueva sin haber cambiado 
    # el estado previamente y de esta manera, el historial que de con los estados bien puestos
    # (por seguridad si la petición de eliminación llega antes que la de cambio de estado)
    if user:
        if turno.estado_turno_usuario.estado not in lista_estados:
            return False
    if not user:
        if turno.estado_turno_empresa.estado not in lista_estados:
            return False
    
    # Modificar solo el atributo eliminado del turno si es NULL por 'u' o 'e' según quién lo haya eliminado. Si ya es 'u' o 'e', 
    # modificar el estado que corresponda de la tabla Historial y luego eliminar turno de la tabla Turno
    if turno.eliminado == None:
        if user:
            historial = models.Historial(
                usuario_id=turno.usuario_id,
                empresa_id=turno.empresa_id,
                fecha_hora=turno.fecha_hora,
                nombre_de_servicio=turno.nombre_de_servicio,
                duracion=turno.duracion,
                precio=turno.precio,
                aclaracion_de_servicio=turno.aclaracion_de_servicio,
                estado_turno_usuario_id=turno.estado_turno_usuario_id,
                estado_turno_empresa_id=None)

            turno.eliminado = 'u' # turno eliminado por el usuario
        if not user:
            historial = models.Historial(
                usuario_id=turno.usuario_id,
                empresa_id=turno.empresa_id,
                fecha_hora=turno.fecha_hora,
                nombre_de_servicio=turno.nombre_de_servicio,
                duracion=turno.duracion,
                precio=turno.precio,
                aclaracion_de_servicio=turno.aclaracion_de_servicio,
                estado_turno_usuario_id=None,
                estado_turno_empresa_id=turno.estado_turno_empresa_id)

            turno.eliminado = 'e' # turno eliminado por la empresa
    
        db.add(historial)
    else:

        # Busco el turno en historial para poder modificarlo
        turno_en_historial = db.query(models.Historial).filter(
                models.Historial.usuario_id == turno.usuario_id,
                models.Historial.empresa_id == turno.empresa_id,
                models.Historial.fecha_hora == turno.fecha_hora).first()
                
        if user:
            # Significa que el turno ya fue movido por la empresa a la tabla Historial y solo queda 
            # agarrar el estado (es un número entero) en el atributo estado_turno_usuario_id del turno de 
            # la tabla Historial y modificarlo por el atributo estado_turno_usuario_id del turno de la tabla Turno.
            e = turno.estado_turno_usuario_id
            turno_en_historial.estado_turno_usuario_id = e
        if not user:
            e = turno.estado_turno_empresa_id
            turno_en_historial.estado_turno_empresa_id = e

        db.delete(turno)

    db.commit()

    return True

# ------------------ CRUD USUARIOS ------------------ #

def get_user(db: Session, user_id: int):
    user = (db.query(models.Usuario)
        .filter(models.Usuario.id == user_id)
        .options(
            joinedload(models.Usuario.telefonos),
            joinedload(models.Usuario.direcciones),
            selectinload(models.Usuario.favoritos).joinedload(models.Empresa.direccion),
            selectinload(models.Usuario.favoritos).joinedload(models.Empresa.telefonos),
            selectinload(models.Usuario.favoritos).selectinload(models.Empresa.servicios),
            joinedload(models.Usuario.miembro_empresas).joinedload(models.Miembro_Empresa.empresa))
        .first())
    return user # user es un objeto de clase Usuario de SQLAlchemy

def revoke_token(db: Session, jti: str, expires_at: datetime):
    rt = Blacklist(jti=jti, expires_at=expires_at)
    db.add(rt)
    db.commit()

# Esta función chequea el token. Se usa cuando el usuario hace algo con el back que no sea registrarse o loguearse
def get_current_user(token: str = Cookie(default=None, # token: str = Cookie() le dice a FastAPI: Busca en la request HTTP una cookie llamada como variables.COOKIE_NAME y pasala a esta función.
                    alias=variables.COOKIE_NAME), db: Session = Depends(get_db)):
    """
    Devuelve el objeto correspondiente según el rol que indique el JWT.
    Puede ser Usuario o Miembro con Empresa.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Token no encontrado")

    try:
        payload = jwt.decode(token, variables.SECRET_KEY, algorithms=[variables.ALGORITHM])
        entity_id = int(payload.get("sub"))
        jti = payload.get("jti")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    # Chequeo en DB si está revocado
    if db.query(models.Blacklist).filter(models.Blacklist.jti == jti).first():
        raise HTTPException(status_code=401, detail="Token revocado")
    
    # Traer usuario
    user = get_user(db, entity_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# Crear usuario
def create_user(db: Session, user: schemas.UserCreate):
    # Verificar si el email o DNI ya existen
    if db.query(models.Usuario).filter(models.Usuario.email == user.email).first():
        raise ValueError("Email ya registrado")

    # Crear el objeto de usuario
    db_user = models.Usuario(
        dni=user.dni,
        apellido=user.apellido,
        nombre=user.nombre,
        email=user.email,
        hashed_password=autenticacion.get_password_hash(user.password))

    db.add(db_user)
    db.commit()
    db.refresh(db_user) # Actualizar el objeto con el ID generado por la BD

    # Agregar teléfonos
    for t in user.telefonos:
        db_tel = models.Telefono(numero=t, usuario_id=db_user.id)
        db.add(db_tel)

    # Agregar direcciones
    for d in user.direcciones:
        db_dir = models.Direccion(
            domicilio=d.domicilio,
            lat=d.lat,
            lng=d.lng,
            piso=d.piso,
            departamento=d.departamento,
            aclaracion=d.aclaracion)

        db.add(db_dir)
        db.commit()
        db.refresh(db_dir)

        # Registrar relación en tabla intermedia
        dir_user = models.Dir_Usuario(direccion_id=db_dir.id, usuario_id=db_user.id)
        db.add(dir_user)

    db.commit()
    db.refresh(db_user) # Actualizar el objeto con el ID generado por la BD

    user = get_user(db, db_user.id)

    return user # user es un objeto de clase Usuario de SQLAlchemy

# Actualizar usuario
def update_user(db: Session, user_id: int, user_update):
    '''
    1. Actualiza los datos simples del usuario (nombre, email, etc.).

    2. Actualiza teléfonos usando una lista de listas [[id, numero], ...]:

        .Si id es 0 → crea nuevo.

        .Si existe → actualiza su número.

        .Si un teléfono que estaba en BD no aparece en la lista → lo elimina.

    3. Actualiza direcciones con DireccionUpdate.

    4. Actualiza favoritos: Si recibe una lista de IDs de empresas favoritas (favoritos), agrega o quita relaciones en la tabla favorito.
    '''
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # ----------------------------
    # 1️⃣ Actualizar campos simples
    # ----------------------------

    # Con user_update.dict(exclude_unset=True) convierto al schema temporalmente en diccionario excluyendo los campos del schema que no fueron enviados en el JSON
    for attr, value in user_update.dict(exclude_unset=True).items():
        if attr == "password":
            # setattr(objeto, atributo, valor) es una función de Python que asigna dinámicamente un valor a un atributo de un objeto
            # en lugar de hacer db_user.nombre = "Tomás" o db_user.email = "tomas@gmail.com" que es menos dinámico para este bucle
            setattr(db_user, "hashed_password", autenticacion.get_password_hash(value))
        elif attr not in ["telefonos", "direcciones", "favoritos"]:
            setattr(db_user, attr, value)
    db.commit()

    # ----------------------------
    # 2️⃣ Actualizar TELÉFONOS
    # ----------------------------

    # user_update sigue siendo un ojeto de clase schemas.UserUpdate
    if user_update.telefonos is not None:
        current_phones = {t.id: t for t in db_user.telefonos}
        new_ids = set()

        for tel in user_update.telefonos:
            if len(tel) != 2:
                continue  # formato inválido
            tel_id, numero = tel

            if tel_id and tel_id in current_phones:
                # Actualizar teléfono existente
                db_tel = current_phones[tel_id]
                db_tel.numero = numero
                new_ids.add(tel_id)
            else:
                # Crear nuevo teléfono
                new_tel = models.Telefono(numero=numero, usuario_id=user_id)
                db.add(new_tel)
        db.commit()

        # Eliminar teléfonos que ya no están en la lista
        for old_id in list(current_phones.keys()):
            if old_id not in new_ids:
                db.query(models.Telefono).filter(models.Telefono.id == old_id).delete()
        db.commit()

    # ----------------------------
    # 3️⃣ Actualizar DIRECCIONES
    # ----------------------------
    if user_update.direcciones is not None:
        current_dirs = {
            du.direccion.id: du.direccion
            for du in db.query(models.Dir_Usuario)
                        .filter(models.Dir_Usuario.usuario_id == user_id)
                        .join(models.Direccion)
                        .all()
        }
        new_dir_ids = set()

        for d in user_update.direcciones:
            if d.id and d.id in current_dirs:
                db_dir = current_dirs[d.id]
                db_dir.domicilio = d.domicilio
                db_dir.lat = d.lat
                db_dir.lng = d.lng
                db_dir.piso = d.piso
                db_dir.departamento = d.departamento
                db_dir.aclaracion = d.aclaracion
                new_dir_ids.add(d.id)
            else:
                # Crear nueva dirección
                db_dir = models.Direccion(
                    domicilio=d.domicilio,
                    lat=d.lat,
                    lng=d.lng,
                    piso=d.piso,
                    departamento=d.departamento,
                    aclaracion=d.aclaracion
                )
                db.add(db_dir)
                db.commit()
                db.refresh(db_dir)
                db.add(models.Dir_Usuario(direccion_id=db_dir.id, usuario_id=user_id))
        db.commit()

        # Eliminar direcciones eliminadas
        for old_id in list(current_dirs.keys()):
            if old_id not in new_dir_ids:
                db.query(models.Dir_Usuario).filter_by(
                    direccion_id=old_id, usuario_id=user_id
                ).delete()
                # Eliminar dirección si nadie más la usa
                used = db.query(models.Dir_Usuario).filter(
                    models.Dir_Usuario.direccion_id == old_id
                ).count()
                if used == 0:
                    db.query(models.Direccion).filter(models.Direccion.id == old_id).delete()
        db.commit()

    # ----------------------------
    # 4️⃣ Actualizar FAVORITOS
    # ----------------------------
    if hasattr(user_update, "favoritos") and user_update.favoritos is not None:
        # Obtener IDs actuales de favoritos del usuario
        current_favs = {
            f.empresa_id for f in db.query(models.Favorito)
                                     .filter(models.Favorito.usuario_id == user_id)
                                     .all()
        }
        new_favs = set(user_update.favoritos)

        # Agregar nuevos favoritos
        for emp_id in new_favs - current_favs:
            db.add(models.Favorito(usuario_id=user_id, empresa_id=emp_id))

        # Eliminar los que ya no están
        for emp_id in current_favs - new_favs:
            db.query(models.Favorito).filter_by(
                usuario_id=user_id, empresa_id=emp_id
            ).delete()
        db.commit()

    db.refresh(db_user)
    return db_user

# Devuelve lista de empresas por nombre y/o servicio
def get_empresas(db: Session, query: str):
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
            joinedload(models.Empresa.direccion),
            joinedload(models.Empresa.servicios))
        .distinct().all() # Devuelve lista sin duplicados
    )
    return empresas # empresas es una lista de objetos de clase Empresa de SQLAlchemy

def get_turnos_disponibles_empresa(db: Session, empresa_id: int):
    emp_disps = (
        db.query(models.Emp_Disp)
        .filter(models.Emp_Disp.empresa_id == empresa_id)
        .options(
            joinedload(models.Emp_Disp.disponibilidad),
            joinedload(models.Emp_Disp.servicios).joinedload(models.Emp_Disp_Ser.servicio))
        .all()
    )

    return emp_disps # emp_disps es una lista de objetos de clase Emp_Disp de SQLAlchemy

def reservar_turno(db: Session, user_id: int, empresa_id: int, fecha_hora: datetime, servicio_id: int, aclaracion_de_servicio: bool):
    # Traer empresa y servicio
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    servicio = db.query(models.Servicio).filter(models.Servicio.id == servicio_id).first()

    dia_hora = auxiliares.extraer_dia_y_hora(fecha_hora)
    dia = dia_hora[0]
    hora = dia_hora[1]

    # Devuelvo una lista de objetos Emp_Disp_Ser con la disponibilidad de esa empresa para con esos servicios en ese día y horario    
    emp_disp_ser_list = db.query(models.Emp_Disp_Ser).join(models.Emp_Disp).join(models.Disponibilidad).filter(
        models.Emp_Disp.empresa_id == empresa_id,
        models.Emp_Disp_Ser.servicio_id == servicio_id,
        models.Disponibilidad.dia == dia,
        models.Disponibilidad.hora == hora).all()


    if not emp_disp_ser_list:
        raise HTTPException(status_code=400, detail="No hay disponibilidad para este servicio en este horario")

    if aclaracion_de_servicio:
        # Si tiene aclaración, la lista emp_disp_ser_list tendrá un solo objeto ya que estamos 
        # haciendo referencia a un servicio en particular en una disponibiliad en particular
        
        # Voy a contar la cantidad de turnos existentes que se superponen con el turno que el cliente quiere sacar (nuevo turno) para este servicio
        turnos_actuales = db.query(models.Turno).filter(
            models.Turno.empresa_id == empresa_id, # turno de la misma empresa
            models.Turno.nombre_de_servicio == servicio.nombre, # turno del mismo servicio
            models.Turno.duracion == servicio.duracion, # turno del mismo servicio
            models.Turno.precio == servicio.precio, # turno del mismo servicio
            models.Turno.aclaracion_de_servicio == servicio.aclaracion, # turno del mismo servicio
            models.Turno.fecha_hora + func.make_interval(mins=models.Turno.duracion) > fecha_hora, # el turno existente termina después de que empieza el nuevo turno
            models.Turno.fecha_hora < fecha_hora + timedelta(minutes=servicio.duracion) # El turno existente empieza antes de que termine el nuevo turno
            ).count()

        emp_disp_ser = emp_disp_ser_list[0]
        if turnos_actuales < emp_disp_ser.cant_turnos_max:
            # Se puede reservar
            turno = models.Turno(
                usuario_id=user_id,
                empresa_id=empresa_id,
                fecha_hora=fecha_hora,
                nombre_de_servicio=servicio.nombre,
                duracion=servicio.duracion,
                precio=servicio.precio,
                aclaracion_de_servicio=servicio.aclaracion,
                estado_turno_usuario_id=1, # confirmado
                estado_turno_empresa_id=1, # confirmado
                eliminado=None)            
            db.add(turno)
            db.commit()
            db.refresh(turno)
            return turno
        else:
            return 'No hay turnos disponibles en ese horario para el servicio elegido'    
    else:
        servicios_totales = [] # Lista de objetos [Servicio, Emp_Disp_Ser]
        for eds in emp_disp_ser_list:
            s = eds.servicio
            servicios_totales.append([s, eds])
        
        servicios_posibles = [] # Lista de objetos Servicio
        for i in servicios_totales:
            servicio_posible = i[0]
            # Voy a contar la cantidad de turnos existentes que se superponen con el turno que el cliente quiere sacar (nuevo turno) para este servicio
            turnos_actuales = db.query(models.Turno).filter(
                models.Turno.empresa_id == empresa_id, # turno de la misma empresa
                models.Turno.nombre_de_servicio == servicio_posible.nombre, # turno del mismo servicio
                models.Turno.duracion == servicio_posible.duracion, # turno del mismo servicio
                models.Turno.precio == servicio_posible.precio, # turno del mismo servicio
                models.Turno.aclaracion_de_servicio == servicio_posible.aclaracion, # turno del mismo servicio
                models.Turno.fecha_hora + func.make_interval(mins=models.Turno.duracion) > fecha_hora, # el turno existente termina después de que empieza el nuevo turno
                models.Turno.fecha_hora < fecha_hora + timedelta(minutes=servicio_posible.duracion) # El turno existente empieza antes de que termine el nuevo turno
                ).count()

            eds = i[1]
            if turnos_actuales < eds.cant_turnos_max:
                servicios_posibles.append(servicio_posible)
                
        if servicios_posibles:
            # Se puede reservar y elegimos uno de los servicios de la lista al azar
            servicio_elegido = random.choice(servicios_posibles)

            turno = models.Turno(
                usuario_id=user_id,
                empresa_id=empresa_id,
                fecha_hora=fecha_hora,
                nombre_de_servicio=servicio_elegido.nombre,
                duracion=servicio_elegido.duracion,
                precio=servicio_elegido.precio,
                aclaracion_de_servicio=servicio_elegido.aclaracion,
                estado_turno_usuario_id=1, # confirmado
                estado_turno_empresa_id=1, # confirmado
                eliminado=None)            
            db.add(turno)
            db.commit()
            db.refresh(turno)
            return turno
        else:
            return 'No hay turnos disponibles en ese horario para el servicio elegido'

def agregar_calificacion(db: Session, empresa_id: int, valor: int):
    try:
        # Guardar calificación
        calif = models.Calificacion(empresa_id=empresa_id, valor=valor)
        db.add(calif)
        db.commit()
        db.refresh(calif)

        # Recalcular promedio
        empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
        if not empresa:
            return False

        califs = db.query(models.Calificacion).filter(models.Calificacion.empresa_id == empresa_id).all()
        promedio = round(sum(c.valor for c in califs) / califs.count(), 2)
        empresa.calificacion = promedio
        db.commit()
        
        return True
    except Exception:
        db.rollback() # rollback() se usa para cancelar todos los cambios pendientes y devolver la sesión a un estado limpio, listo para nuevas operaciones.
        return False  # <-- Si hubo un error en la base de datos

# ------------------ CRUD EMPRESAS ------------------ #

def get_empresa(db: Session, empresa_id: int):
    empresa = db.query(models.Empresa).options(
        joinedload(models.Empresa.direccion),
        joinedload(models.Empresa.telefonos),
        selectinload(models.Empresa.servicios),
        selectinload(models.Empresa.miembros).joinedload(models.Miembro_Empresa.usuario),
        (selectinload(models.Empresa.disponibilidades) # Trae todas las filas de Emp_Disp asociadas a la Empresa
            .joinedload(models.Emp_Disp.disponibilidad) # Para cada Emp_Disp que ya se cargó, trae la Disponibilidad asociada
            .selectinload(models.Emp_Disp.servicios) # Trae todas las filas de Emp_Disp_Ser asociadas a cada Emp_Disp.
            .joinedload(models.Emp_Disp_Ser.servicio) # Para cada Emp_Disp_Ser, trae el objeto Servicio
        )
        ).filter(models.Empresa.id == empresa_id).first()
    return empresa # empresa es un objeto de clase Empresa de SQLAlchemy

# Crear usuario
def create_empresa(db: Session, empresa: schemas.EmpresaCreate):

    # Crear el objeto de empresa
    db_empresa = models.Empresa(
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2)

    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa) # Actualizar el objeto con el ID generado por la BD

    # Agregar teléfonos
    for t in empresa.telefonos:
        db_tel = models.Telefono(numero=t, empresa_id=db_empresa.id)
        db.add(db_tel)

    # Agregar dirección
    db_dir = models.Direccion(
        empresa_id=db_empresa.id,
        domicilio=empresa.direccion.domicilio,
        lat=empresa.direccion.lat,
        lng=empresa.direccion.lng,
        piso=empresa.direccion.piso,
        departamento=empresa.direccion.departamento,
        aclaracion=empresa.direccion.aclaracion)

    db.add(db_dir)

    db.commit()
    db.refresh(db_empresa) # Actualizar el objeto con el ID generado por la BD

    return db_empresa # db_empresa es un objeto de clase Empresa de SQLAlchemy

def asignar_rol(db: Session, usuario_id: int, empresa_id: int, rol: str):

    # Verificar si ya existe
    miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()
    
    if existing:
        raise ValueError("El usuario ya es miembro de esta empresa")
    
    db_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol=rol)
    db.add(db_miembro)
    db.commit()

def verificar_rol_en_empresa(db: Session, usuario_id: int, empresa_id: int):
    """
    Verifica que un usuario pertenece a una empresa y devuelve su rol.
    Lanza HTTPException 403 si no cumple.
    """
    miembro = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()

    if not miembro:
        raise HTTPException(status_code=403, detail="Usuario no pertenece a la empresa")

    return miembro.rol

def update_empresa(db: Session, empresa_id: int, empresa_update: schemas.EmpresaUpdate):
    db_emp = get_empresa(db, empresa_id)
    if not db_emp:
        return None

    # ----------------------------
    # 1️⃣ Actualizar campos simples
    # ----------------------------
    for attr, value in empresa_update.dict(exclude_unset=True).items():
        if attr not in ["telefonos", "direccion"]:
            setattr(db_emp, attr, value)
    db.commit()

    # ----------------------------
    # 2️⃣ Actualizar TELÉFONOS
    # ----------------------------
    if empresa_update.telefonos is not None:
        current_phones = {t.id: t for t in db_emp.telefonos}
        new_ids = set()

        if len(empresa_update.telefonos) == 0:
            # Eliminar todos
            for t in list(current_phones.values()):
                db.delete(t)
        else:
            for tel in empresa_update.telefonos:
                if len(tel) != 2:
                    continue
                tel_id, numero = tel

                if tel_id and tel_id in current_phones:
                    db_tel = current_phones[tel_id]
                    db_tel.numero = numero
                    new_ids.add(tel_id)
                else:
                    new_tel = models.Telefono(numero=numero, empresa_id=empresa_id)
                    db.add(new_tel)

            # Eliminar los que ya no están
            for old_id in list(current_phones.keys()):
                if old_id not in new_ids:
                    db.query(models.Telefono).filter(models.Telefono.id == old_id).delete()

        db.commit()

    # ----------------------------
    # 3️⃣ Actualizar DIRECCIÓN
    # ----------------------------
    if empresa_update.direccion is not None:
        d = empresa_update.direccion
        if db_emp.direccion:
            db_dir = db_emp.direccion
            if d.id and db_dir.id == d.id:
                db_dir.domicilio = d.domicilio
                db_dir.lat = d.lat
                db_dir.lng = d.lng
                db_dir.piso = d.piso
                db_dir.departamento = d.departamento
                db_dir.aclaracion = d.aclaracion
            else:
                # Reemplazar por nueva dirección
                db.delete(db_emp.direccion)
                new_dir = models.Direccion(
                    empresa_id=empresa_id,
                    domicilio=d.domicilio,
                    lat=d.lat,
                    lng=d.lng,
                    piso=d.piso,
                    departamento=d.departamento,
                    aclaracion=d.aclaracion)
                db.add(new_dir)
        else:
            # Crear nueva dirección
            new_dir = models.Direccion(
                empresa_id=empresa_id,
                domicilio=d.domicilio,
                lat=d.lat,
                lng=d.lng,
                piso=d.piso,
                departamento=d.departamento,
                aclaracion=d.aclaracion)
            db.add(new_dir)

        db.commit()

    db.refresh(db_emp)
    return db_emp

def update_servicios_empresa(db: Session, empresa_id: int, servicios_update: schemas.ServiciosUpdateIn):

    db_emp = get_empresa(db, empresa_id)
    if not db_emp:
        return None
    
    # Trato un servicio completo a la vez   
    for s in servicios_update:
        # Crear o actualizar servicio
        if s.id:
            servicio = db.query(models.Servicio).filter_by(id=s.id, empresa_id=empresa_id).first()
            if not servicio:
                continue
            servicio.nombre = s.nombre
            servicio.duracion = s.duracion
            servicio.precio = s.precio
        else:
            servicio = models.Servicio(
                empresa_id=empresa_id,
                nombre=s.nombre,
                duracion=s.duracion,
                precio=s.precio,
                aclaracion=s.aclaracion)
            db.add(servicio)
            db.commit()
            db.refresh(servicio)
        
        # Procesar disponibilidades por día y rango horario
        for disp_range in s.disponibilidades:
            dia = disp_range.dia
            inicio = disp_range.hora_inicio
            fin = disp_range.hora_fin
            cant_max = disp_range.cant_turnos_max

            current_time = inicio
            while current_time >= inicio and current_time <= fin:
                # 1️⃣ Crear o traer disponibilidad
                disp = db.query(models.Disponibilidad).filter_by(dia=dia, hora=current_time).first()
                
                # 2️⃣ Asociar con Emp_Disp
                emp_disp = db.query(models.Emp_Disp).filter_by(empresa_id=empresa_id, disponibilidad_id=disp.id).first()
                if not emp_disp:
                    emp_disp = models.Emp_Disp(empresa_id=empresa_id, disponibilidad_id=disp.id)
                    db.add(emp_disp)
                    db.commit()
                    db.refresh(emp_disp)
                
                # 3️⃣ Asociar servicio a Emp_Disp_Ser con cant_turnos_max
                emp_disp_ser = db.query(models.Emp_Disp_Ser).filter_by(emp_disp_id=emp_disp.id, servicio_id=servicio.id).first()
                if not emp_disp_ser:
                    emp_disp_ser = models.Emp_Disp_Ser(
                        emp_disp_id=emp_disp.id,
                        servicio_id=servicio.id,
                        cant_turnos_max=cant_max)
                    db.add(emp_disp_ser)
                else:
                    emp_disp_ser.cant_turnos_max = cant_max
                
                db.commit()
                # Avanzar 5 minutos
                current_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=5)).time()

    db.refresh(db_emp)
    return db_emp

def eliminar_servicios_empresa(db: Session, empresa_id: int, servicios_delete: schemas.ServiciosDeleteIn):
    # Traer la empresa
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        return None

    # Iterar sobre los IDs de servicios a eliminar
    for servicio_id in servicios_delete.servicios:
        servicio = db.query(models.Servicio).filter(
            models.Servicio.id == servicio_id,
            models.Servicio.empresa_id == empresa_id).first()

        if not servicio:
            continue  # Si el servicio no pertenece a la empresa o no existe, lo saltamos

        # 1️⃣ Eliminar asociaciones en Emp_Disp_Ser
        emp_disp_sers = db.query(models.Emp_Disp_Ser).join(models.Emp_Disp).filter(
            models.Emp_Disp.empresa_id == empresa_id,
            models.Emp_Disp_Ser.servicio_id == servicio_id).all()

        for eds in emp_disp_sers:
            db.delete(eds)

        # 2️⃣ Eliminar Emp_Disp sin servicios asociados
        emp_disps = db.query(models.Emp_Disp).filter(models.Emp_Disp.empresa_id == empresa_id).all()
        for ed in emp_disps:
            tiene_servicios = db.query(models.Emp_Disp_Ser).filter(models.Emp_Disp_Ser.emp_disp_id == ed.id).count()
            if tiene_servicios == 0:
                db.delete(ed)

        # 3️⃣ Eliminar el servicio en sí
        db.delete(servicio)

    # Guardar cambios
    db.commit()

    # Devolver empresa
    return empresa
