'''
Este módulo es para la sección cliente del usuario
'''
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Cookie, Response, HTTPException # Depends se usa para declarar dependencias en FastAPI (por ejemplo, obtener la sesión de base de datos).
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, schemas, crud, autenticacion, auxiliares, variables
from core.database import get_db

router = APIRouter(prefix="/users", tags=["Usuarios"])
# APIRouter() crea un router, que es como un mini “sub-aplicación” dentro de FastAPI.
# prefix="/users" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Usuarios"] sirve para organizar la documentación automática de Swagger (/docs).

# Crear usuario
@router.post("/", response_model=schemas.UserConRolesOut) # @router.post("/users/") indica que esta función responde a POST en /users/.
def create_user(user: schemas.UserCreate, response: Response, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario en la base de datos (registro).
    - Verifica que el email y el DNI no estén ya registrados.
    - Hashea la contraseña antes de guardar.
    - Devuelve el usuario creado.
    """
    try:
        user = crud.create_user(db, user) # Devuelve un objeto de clase Usuario (más completo que db_user (con sus relationships)) de SQLAlchemy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Crear token con duración de 1 día
    token = autenticacion.create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=variables.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Guardar token en cookie
    response.set_cookie(
        key=variables.COOKIE_NAME,
        value=token,
        domain=variables.COOKIE_DOMAIN,
        httponly=True,
        secure=variables.COOKIE_SECURE,
        samesite=variables.COOKIE_SAMESITE,
        max_age=60*variables.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Convertimos el objeto de clase Usuario SQLAlchemy al objeto de clase UsuarioLoginOut de Pydantic
    us = auxiliares.convertir_orm_pydantic_usuario(user)

    return UserConRolesOut(usuario=us, roles=[])

# Usuario se loguea
@router.post("/login", response_model=schemas.UserConRolesOut)
def login_user(user: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = autenticacion.authenticate(db, user.email, user.password) # db_user es un objeto de clase Usuario de SQLAlchemy
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # Crear token con duración de 1 día
    token = autenticacion.create_access_token(
        data={"sub": db_user.id},
        expires_delta=timedelta(minutes=variables.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Guardar token en cookie
    response.set_cookie(
        key=variables.COOKIE_NAME,
        value=token,
        domain=variables.COOKIE_DOMAIN,
        httponly=True,
        secure=variables.COOKIE_SECURE,
        samesite=variables.COOKIE_SAMESITE,
        max_age=60*variables.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    user = crud.get_user(db, db_user.id) # user ahora es un objeto de clase Usuario (más completo que db_user (con sus relationships)) de SQLAlchemy
    turnos = crud.get_turnos(db, db_user.id)
    
    us = auxiliares.convertir_orm_pydantic_usuario(user, turnos_del_usuario=turnos) # us es un objeto de clase UsuarioLoginOut de Pydantic

    # Traer roles en empresas
    roles = db.query(models.Miembro_Empresa).filter_by(usuario_id=db_user.id).all()

    lista_roles = [RolEmpresaOut(rol=m.rol, empresa_id=m.empresa_id, 
        nombre=m.empresa.nombre) for m in roles] # lista_roles es una lista de objetos de clase RolEmpresaOut de Pydantic

    return UserConRolesOut(usuario=us, roles=lista_roles) # Devuelve lista vacía si no trabaja en ninguna empresa

@router.get("/me", response_model=schemas.UserConRolesOut)
def me(current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    '''
    Esto es para si abre la app o dominio y ya estaba logueado y el navegador ya tiene 
    la cookie y asi el usuario no tiene que poner de vuelta la contraseña y el email.
    '''
    user = crud.get_user(db, current_user.id)
    turnos = crud.get_turnos(db, current_user.id)
    
    us = auxiliares.convertir_orm_pydantic_usuario(user, turnos_del_usuario=turnos) # us es un objeto de clase UsuarioLoginOut de Pydantic

    # Traer roles en empresas
    roles = db.query(models.Miembro_Empresa).options(joinedload(models.Miembro_Empresa.empresa)).filter_by(usuario_id=current_user.id).all()

    lista_roles = [RolEmpresaOut(rol=m.rol, empresa_id=m.empresa_id, 
        nombre=m.empresa.nombre) for m in roles] # lista_roles es una lista de objetos de clase RolEmpresaOut de Pydantic

    return schemas.UserConRolesOut(usuario=us, roles=lista_roles)

# Usuario cierra sesión
@router.post("/logout")
def logout_user(response: Response, current_user: models.Usuario = Depends(crud.get_current_user), 
    db: Session = Depends(get_db), token: str = Cookie(default=None, alias=variables.COOKIE_NAME)):
    '''
    Mientras no se borre el historial ni las cookies del navegador (chrome por ejemplo),
    la cookie seguirá existiendo hasta que pasen ese día (24 h).
    Entonces, si el usuario cierra y vuelve a abrir el navegador, el token sigue estando ahí y sigue siendo válido.
    Si la cookie se borra (por logout o por vencimiento), el backend ya no podrá validarlo → 401.
    2 usuarios distintos no pueden tener dos sesiones distintas del mismo dominio abiertas en el mismo tipo de navegador en la misma compu 
    (por más que sean 2 ventanas del mismo tipo de navegador).
    '''
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = datetime.utcfromtimestamp(payload.get("exp"))
            revoke_token(db, jti=jti, expires_at=exp)
        except Exception:
            pass

    response.delete_cookie(variables.COOKIE_NAME)
    return {"msg": "Logout exitoso"}

# Actualizar usuario (datos simples, telefonos, direcciones y favoritos)
@router.put("/{user_id}", response_model=schemas.UserUpdateOut)
def update_user(user_update: schemas.UserUpdate, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    db_user = crud.update_user(db, user_id, user_update)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user = crud.get_user(db, db_user.id) # user ahora es un objeto de clase Usuario (con sus relationships actualizadas) de SQLAlchemy
    
    us = auxiliares.convertir_orm_pydantic_usuario(user, update=True)

    return us # us es un objeto de clase UsuarioUpdateOut de Pydantic

# Usuario reserva turno
@router.post("/turnos/reservar", response_model=schemas.TurnoReservadoOut)
def reservar_turno(reserva: schemas.ReservaTurnoIn, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    # Verificar empresa y servicio
    empresa = db.query(models.Empresa).filter(models.Empresa.id == reserva.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    servicio = db.query(models.Servicio).filter(models.Servicio.id == reserva.servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    turno = crud.reservar_turno(db, current_user.id, reserva.empresa_id, reserva.fecha_hora, reserva.servicio_id, reserva.aclaracion_de_servicio)

    if isinstance(turno, models.Turno):
        turno_out = schemas.TurnoOut(
            id=turno.id,
            empresa=empresa.nombre,
            direccion=schemas.DireccionOut(
                id=empresa.direccion.id,
                domicilio=empresa.direccion.domicilio,
                lat=empresa.direccion.lat,
                lng=empresa.direccion.lng,
                piso=empresa.direccion.piso,
                departamento=empresa.direccion.departamento,
                aclaracion=empresa.direccion.aclaracion),
            fecha_hora=turno.fecha_hora,
            nombre_de_servicio=turno.nombre_de_servicio,
            duracion=turno.duracion,
            precio=turno.precio,
            aclaracion_de_servicio=turno.aclaracion_de_servicio,
            estado_turno=turno.estado_turno_usuario.estado)
        return schemas.TurnoReservadoOut(message="Turno reservado con éxito", turno=turno_out)
    if isinstance(turno, str):
        return schemas.TurnoReservadoOut(message=turno)

@router.post("/{empresa_id}/calificacion")
def calificar_empresa(calificacion_recibida: schemas.Calificacion, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    exito = crud.agregar_calificacion(db, calificacion_recibida.empresa_id, calificacion_recibida.valor)
    if not exito:
        raise HTTPException(status_code=400, detail="No se pudo guardar la calificación")
    
    return {"empresa_id": calificacion_recibida.empresa_id, "calificacion_guardada": True}

# Devuelve lista de empresas (sin duplicados) con coincidencia parcial de nombre y/o rubros haciendo, por ejemplo, GET /users/search/empresa?query=peluq
@router.get("/search/empresa", response_model=list[schemas.EmpresaOut])
def get_empresas(query: str, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    empresas = crud.get_empresas(db, query) # empresas es una lista de objetos de clase Empresa de SQLAlchemy
    if not empresas:
        raise HTTPException(status_code=404, detail="No se encontraron empresas que coincidan con la búsqueda")
    
    resultados = []
    for e in empresas:
        resultados.append(schemas.EmpresaOut(
            id=e.id,
            cuit=e.cuit,
            nombre=e.nombre,
            email=e.email,
            rubro=e.rubro,
            rubro2=e.rubro2,
            calificacion=e.calificacion,
            telefonos=[t.numero for t in e.telefonos],
            direccion=schemas.DireccionOut(
                id=e.direccion.id,
                domicilio=e.direccion.domicilio,
                lat=e.direccion.lat,
                lng=e.direccion.lng,
                piso=e.direccion.piso,
                departamento=e.direccion.departamento,
                aclaracion=e.direccion.aclaracion),
            servicios=list({s.nombre for s in e.servicios}) # Evita duplicados
        ))
    return resultados # resultados es una lista de objetos de clase EmpresaOut de Pydantic

# Se envía al hacer click en la empresa
@router.get("/empresas/{empresa_id}/turnos_disponibles") # No hay schema Pydantic en este endpoint
def get_turnos_disponibles_empresa(empresa_id: int, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    emp_disps = crud.get_turnos_disponibles_empresa(db, empresa_id) # emp_disps es una lista de objetos de clase Emp_Disp de SQLAlchemy
    if not emp_disps:
        raise HTTPException(status_code=404, detail="No hay turnos disponibles para esta empresa")
    
    turnos_disponibles = []
    servicios_dict = {}

    for ed in emp_disps:  # ed es un objeto Emp_Disp
        servicios_ids = []
        for eds in ed.servicios:  # eds es un objeto Emp_Disp_Ser
            s = eds.servicio  # s es el objeto Servicio
            servicios_dict[s.id] = {"id": s.id, "nombre_de_servicio": s.nombre, "duracion": s.duracion, 
                                    "precio": s.precio, "aclaracion_de_servicio": s.aclaracion}
            servicios_ids.append(s.id)

        turnos_disponibles.append({
            "id": ed.id,
            "dia": ed.disponibilidad.dia,
            "hora": ed.disponibilidad.hora.strftime("%H:%M"), # Esto se hace porque no pasa primero por la validación y conversión de Pydantic (atributo tipo time)
            "servicios": servicios_ids})

    return {"empresa_id": empresa_id, "turnos_disponibles": turnos_disponibles, "servicios_dict": servicios_dict}

# Devuelve todos los turnos que el usuario ya completó (tabla Historial) (el primero devuelto será el más reciente)
@router.get("/{user_id}/historial", response_model=schemas.HistorialResponse)
def get_historial_turnos(current_user: models.Usuario = Depends(crud.get_current_user), 
    db: Session = Depends(get_db), before: Optional[datetime] = None):
    
    user_id = current_user.id
    f_h_ultima = before or datetime.max # si el before fue pasado, se toma, y si no, se toma datetime.max

    historial, ultimo_cursor = crud.get_historial_turnos(
        db, user_id, fecha_hora_ultima=f_h_ultima) # historial es una lista de objetos de clase Historial de SQLAlchemy

    if not historial:
        raise HTTPException(status_code=404, detail="No hay historial de turnos")
    
    resultados = []
    for h in historial:
        resultados.append(schemas.HistorialOut(
            empresa=h.empresa.nombre,
            fecha_hora=h.fecha_hora,
            nombre_de_servicio=h.nombre_de_servicio,
            duracion=h.duracion,
            precio=h.precio,
            aclaracion_de_servicio=h.aclaracion_de_servicio,
            estado_turno=h.estado_turno_usuario.estado))
    
    respuesta = schemas.HistorialResponse(
        historial=resultados, # resultados es una lista de objetos de clase HistorialOut de Pydantic
        ultimo_cursor=ultimo_cursor) # ultimo_cursor volverá si el usuario pide más historial
    
    return respuesta

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.put("/{user_id}/turnos/", response_model=schemas.TurnoOut)
def modificar_turno_usuario(turno_update: schemas.TurnoUpdate, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    turno = db.query(models.Turno).filter(models.Turno.id == turno_update.id, models.Turno.usuario_id == user_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    turno_modificado = crud.modificar_turno(db, turno, turno_update.estado_turno)

    # Convertir el objeto SQLAlchemy a Pydantic
    turno_out = schemas.TurnoOut(
        id=turno_modificado.id,
        empresa=turno_modificado.empresa.nombre,
        direccion=schemas.DireccionOut(
            id=turno_modificado.empresa.direccion.id,
            domicilio=turno_modificado.empresa.direccion.domicilio,
            lat=turno_modificado.empresa.direccion.lat,
            lng=turno_modificado.empresa.direccion.lng,
            piso=turno_modificado.empresa.direccion.piso,
            departamento=turno_modificado.empresa.direccion.departamento,
            aclaracion=turno_modificado.empresa.direccion.aclaracion),
        fecha_hora=turno_modificado.fecha_hora,
        nombre_de_servicio=turno_modificado.nombre_de_servicio,
        duracion=turno_modificado.duracion,
        precio=turno_modificado.precio,
        aclaracion_de_servicio=turno_modificado.aclaracion_de_servicio,
        estado_turno=turno_modificado.estado_turno_usuario.estado)

    return turno_out

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
@router.delete("/{user_id}/turnos/{turno_id}")
def agregar_turno_historial_usuario(turno_id: int, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    turno = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario),
        joinedload(models.Turno.estado_turno_empresa)).filter(models.Turno.id == turno_id, models.Turno.usuario_id == user_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    exito = crud.agregar_turno_historial(db, turno, variables.LISTA_PARCIAL_DE_ESTADOS)

    if exito:
        # Mando el id para que el frontend lo elimine del front y lo pase a historial y así no tener que enviarle todos sus turnos de vuelta
        return {"msg": "Turno movido al historial correctamente", "turno_id": turno_id}
    else:
        raise HTTPException(status_code=400, detail="Debe cambiar el estado antes de mover al historial al turno")


# ---------------- RECUPERAR CONTRASEÑA ---------------- #

# ---------------- FORGOT PASSWORD ---------------- #
@router.post("/forgot_password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    try:
        token = autenticacion.generate_password_reset_token(db, email)
        autenticacion.send_reset_email(email, token)
    except ValueError:
        pass  # No revelamos si el email existe o no

    return {"message": "Revisá tu correo para resetear la contraseña."}

# ---------------- RESET PASSWORD ---------------- #
@router.post("/reset_password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    try:
        autenticacion.reset_password(db, token, new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Contraseña actualizada correctamente."}
