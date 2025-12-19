'''
Este módulo es para la sección cliente del usuario
'''
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Cookie, Response, HTTPException # Depends se usa para declarar dependencias en FastAPI (por ejemplo, obtener la sesión de base de datos).
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.
from jose import jwt

from core import models, schemas, crud, autenticacion, auxiliares, variables, mensajes
from core.database import get_db

router = APIRouter(prefix="/users", tags=["Usuarios"])
# APIRouter() crea un router, que es como un mini “sub-aplicación” dentro de FastAPI.
# prefix="/users" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Usuarios"] sirve para organizar la documentación automática de Swagger (/docs).

# Crear usuario
@router.post("/") # @router.post("/users/") indica que esta función responde a POST en /users/.
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

    return {"ok": True}

# Usuario se loguea
@router.post("/login")
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
    
    return {"ok": True}

@router.get("/me", response_model=schemas.UserLoginOut)
def me(current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):
    '''
    Esto es para que cuando el creat o login dé el OK, el navegador pida los datos del
    usuario para el HTML del panel del usuario.
    También se usa para que el usuario entre a su panel de una cuando abra la app o dominio y ya estaba logueado y 
    el navegador ya tiene la cookie y así el usuario no tiene que poner de vuelta la contraseña y el email.
    '''
    user = crud.get_user(db, current_user.id)
    turnos = crud.get_turnos(db, current_user.id)
    
    us = auxiliares.convertir_orm_pydantic_usuario(user, turnos_del_usuario=turnos) # us es un objeto de clase UsuarioLoginOut de Pydantic

    return us

# Actualizar usuario (datos simples, telefonos, direcciones y favoritos)
@router.put("/me", response_model=schemas.UserUpdateOut)
def update_user(user_update: schemas.UserUpdate, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    user_id = current_user.id
    db_user = crud.update_user(db, user_id, user_update)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user = crud.get_user(db, db_user.id) # user ahora es un objeto de clase Usuario (con sus relationships actualizadas) de SQLAlchemy
    
    us = auxiliares.convertir_orm_pydantic_usuario(user, update=True)

    return us # us es un objeto de clase UsuarioUpdateOut de Pydantic

# Usuario cierra sesión
@router.post("/logout")
def logout_user(response: Response, current_user: models.Usuario = Depends(crud.get_current_user), 
    db: Session = Depends(get_db), token: str = Cookie(default=None, alias=variables.COOKIE_NAME)):
    '''
    Mientras no se borre el historial ni las cookies del navegador (chrome por ejemplo),
    la cookie seguirá existiendo hasta que pasen ese día (24 hs).
    Entonces, si el usuario cierra y vuelve a abrir el navegador, el token seguirá estando ahí y seguirá siendo válido.
    Si la cookie se borra (por logout o por vencimiento), el backend ya no podrá validarlo → 401.
    2 usuarios distintos no pueden tener dos sesiones distintas del mismo dominio abiertas en el mismo tipo de navegador en la misma compu 
    (por más que sean 2 ventanas del mismo tipo de navegador).
    '''
    if token:
        try:
            payload = jwt.decode(token, variables.SECRET_KEY, algorithms=[variables.ALGORITHM])
            jti = payload.get("jti")
            exp = datetime.utcfromtimestamp(payload.get("exp"))
            crud.revoke_token(db, jti=jti, expires_at=exp)
        except Exception:
            pass

    response.delete_cookie(
        key=variables.COOKIE_NAME,
        domain=variables.COOKIE_DOMAIN,
        path="/", # path por defecto suele ser "/"
        samesite=variables.COOKIE_SAMESITE,
        secure=variables.COOKIE_SECURE
    )
    return {"msg": "Logout exitoso"}

@router.get("/mis_empresas", response_model=list[schemas.RolEmpresaOut])
def get_roles(current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Traer roles en empresas
    roles = db.query(models.Miembro_Empresa).options(joinedload(models.Miembro_Empresa.empresa)).filter_by(usuario_id=current_user.id).all()

    lista_roles = [schemas.RolEmpresaOut(rol=m.rol, empresa_id=m.empresa_id, nombre_empresa=m.empresa.nombre, 
        logo_empresa=auxiliares.codificar_logo(m.empresa.logo)) for m in roles]
    
    return lista_roles # lista_roles es una lista de objetos de clase RolEmpresaOut de Pydantic

@router.post("/calificacion")
def calificar_empresa(calificacion_recibida: schemas.Calificacion, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    exito = crud.agregar_calificacion(db, calificacion_recibida.empresa_id, calificacion_recibida.valor)
    if not exito:
        raise HTTPException(status_code=400, detail="No se pudo guardar la calificación")
    
    return {"empresa_id": calificacion_recibida.empresa_id, "calificacion_guardada": True}

# Devuelve lista de empresas (sin duplicados) con coincidencia parcial de nombre y/o rubros haciendo, por ejemplo, GET /users/search/empresa?query=peluq
@router.get("/empresas/search", response_model=list[schemas.EmpresaOut])
def get_empresas(query: str, lat: float, lng: float, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    empresas = crud.get_empresas(db, query, lat, lng) # empresas es una lista de objetos de clase Empresa de SQLAlchemy

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
                calle=e.direccion.calle,
                altura=e.direccion.altura,
                localidad=e.direccion.localidad,
                departamento=e.direccion.departamento,
                provincia=e.direccion.provincia,
                pais=e.direccion.pais,
                lat=e.direccion.lat,
                lng=e.direccion.lng,
                aclaracion=e.direccion.aclaracion),
            logo=auxiliares.codificar_logo(e.logo)
        ))
    return resultados # resultados es una lista de objetos de clase EmpresaOut de Pydantic

# Se envía al hacer click en la empresa
@router.get("/empresas/{empresa_id}/turnos_disponibles", response_model=list[schemas.ServicioConTurnosOut])
def get_turnos_disponibles_empresa(empresa_id: int, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    servicios = crud.get_turnos_disponibles_empresa(db, empresa_id) # servicios es una lista de objetos de clase Servicio de SQLAlchemy
    if not servicios:
        raise HTTPException(status_code=404, detail="No hay turnos disponibles para esta empresa")
    
    turnos = crud.get_turnos_confirmados_empresa(db, empresa_id)

    turnos_por_servicio: dict[int, list[schemas.TurnoActualDelServicio]] = {}

    for t in turnos:
        turno_out = schemas.TurnoActualDelServicio(
            id=t.id,
            fecha_hora=t.fecha_hora,
            duracion=t.duracion
        )

        turnos_por_servicio.setdefault(t.servicio_id, []).append(turno_out)

    servicios_out = []

    for s in servicios:
        disponibilidades_out = []

        # recorrer todas las disponibilidades asociadas
        for sd in s.ser_disps:
            d = sd.disponibilidad
            disponibilidades_out.append(
                schemas.DisponibilidadOut(
                    id=d.id,
                    dia=d.dia,
                    hora=d.hora.strftime("%H:%M"), # para el output, JSON no reconoce el tipo time y por eso se lo envía como string
                    cant_turnos_max=sd.cant_turnos_max
                )
            )
        
        profesional = s.profesional
        us = profesional.usuario if profesional and profesional.usuario else None

        servicio_out = schemas.ServicioConTurnosOut(
            id=s.id,
            nombre=s.nombre,
            duracion=s.duracion,
            precio=s.precio,
            aclaracion=s.aclaracion,
            profesional_id=s.miembro_empresa_id,
            profesional_dni=us.dni if us else None,
            profesional_apellido=us.apellido if us else None,
            profesional_nombre=us.nombre if us else None,
            disponibilidades=disponibilidades_out,
            turnos_actuales=turnos_por_servicio.get(s.id, []))

        servicios_out.append(servicio_out)

    return servicios_out

# Devuelve todos los turnos que el usuario ya completó (tabla Historial) (el primero devuelto será el más reciente)
@router.get("/historial", response_model=schemas.HistorialResponse)
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
            profesional_dni=h.profesional.dni if h.profesional else None,
            profesional_apellido=h.profesional.apellido if h.profesional else None,
            profesional_nombre=h.profesional.nombre if h.profesional else None,
            estado_turno=h.estado_turno_usuario.estado))
    
    respuesta = schemas.HistorialResponse(
        historial=resultados, # resultados es una lista de objetos de clase HistorialOut de Pydantic
        ultimo_cursor=ultimo_cursor) # ultimo_cursor volverá si el usuario pide más historial
    
    return respuesta

# Usuario reserva turno
@router.post("/turnos", response_model=schemas.TurnoReservadoOut)
def reservar_turno(reserva: schemas.ReservaTurnoIn, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verificar empresa y servicio
    empresa = db.query(models.Empresa).filter(models.Empresa.id == reserva.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    servicio = db.query(models.Servicio).filter(models.Servicio.id == reserva.servicio_id).first()
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    turn = crud.reservar_turno(db, current_user.id, reserva.empresa_id, 
        reserva.fecha_hora, reserva.servicio_id, reserva.profesional_id)
    
    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion),
        joinedload(models.Turno.estado_turno_usuario),
        joinedload(models.Turno.estado_turno_empresa),
        joinedload(models.Turno.recordatorio)).filter(models.Turno.id == turn.id).first()

    if isinstance(turno, models.Turno):
        turno_out = schemas.TurnoOut(
            id=turno.id,
            empresa_id=empresa.id,
            empresa=empresa.nombre,
            logo_empresa=auxiliares.codificar_logo(empresa.logo),
            direccion=schemas.DireccionOut(
                id=empresa.direccion.id,
                calle=empresa.direccion.calle,
                altura=empresa.direccion.altura,
                localidad=empresa.direccion.localidad,
                departamento=empresa.direccion.departamento,
                provincia=empresa.direccion.provincia,
                pais=empresa.direccion.pais,
                lat=empresa.direccion.lat,
                lng=empresa.direccion.lng,
                aclaracion=empresa.direccion.aclaracion),
            fecha_hora=turno.fecha_hora,
            nombre_de_servicio=turno.nombre_de_servicio,
            duracion=turno.duracion,
            precio=turno.precio,
            aclaracion_de_servicio=turno.aclaracion_de_servicio,
            profesional_dni=turno.profesional.dni if turno.profesional else None,
            profesional_apellido=turno.profesional.apellido if turno.profesional else None,
            profesional_nombre=turno.profesional.nombre if turno.profesional else None,
            estado_turno=turno.estado_turno_usuario.estado,
            recordatorio=turno.recordatorio.minutos_antes if turno.recordatorio else None)
        return schemas.TurnoReservadoOut(message="Turno reservado con éxito", turno=turno_out)
    if isinstance(turno, str):
        return schemas.TurnoReservadoOut(message=turno)

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.put("/turnos", response_model=schemas.TurnoOut)
def modificar_turno_usuario(turno_update: schemas.TurnoUpdate, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    user_id = current_user.id
    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.empresa)).filter(
            models.Turno.id == turno_update.id, models.Turno.usuario_id == user_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    turno_modificado = crud.modificar_turno(db, turno, turno_update.estado_turno, turno_update.recordatorio)

    # Convertir el objeto SQLAlchemy a Pydantic
    turno_out = schemas.TurnoOut(
        id=turno_modificado.id,
        empresa_id=turno_modificado.empresa_id,
        empresa=turno_modificado.empresa.nombre,
        logo_empresa=auxiliares.codificar_logo(turno_modificado.empresa.logo),
        direccion=schemas.DireccionOut(
            id=turno_modificado.empresa.direccion.id,
            calle=turno_modificado.empresa.direccion.calle,
            altura=turno_modificado.empresa.direccion.altura,
            localidad=turno_modificado.empresa.direccion.localidad,
            departamento=turno_modificado.empresa.direccion.departamento,
            provincia=turno_modificado.empresa.direccion.provincia,
            pais=turno_modificado.empresa.direccion.pais,
            lat=turno_modificado.empresa.direccion.lat,
            lng=turno_modificado.empresa.direccion.lng,
            aclaracion=turno_modificado.empresa.direccion.aclaracion),
        fecha_hora=turno_modificado.fecha_hora,
        nombre_de_servicio=turno_modificado.nombre_de_servicio,
        duracion=turno_modificado.duracion,
        precio=turno_modificado.precio,
        aclaracion_de_servicio=turno_modificado.aclaracion_de_servicio,
        profesional_dni=turno_modificado.profesional.dni if turno_modificado.profesional else None,
        profesional_apellido=turno_modificado.profesional.apellido if turno_modificado.profesional else None,
        profesional_nombre=turno_modificado.profesional.nombre if turno_modificado.profesional else None,
        estado_turno=turno_modificado.estado_turno_usuario.estado,
        recordatorio=turno_modificado.recordatorio.minutos_antes if turno_modificado.recordatorio else None)

    return turno_out

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
@router.delete("/turnos/{turno_id}")
def agregar_turno_historial_usuario(turno_id: int, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    user_id = current_user.id

    turno = db.query(models.Turno).options(
        joinedload(models.Turno.usuario),
        joinedload(models.Turno.profesional),
        joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion),
        joinedload(models.Turno.estado_turno_usuario),
        joinedload(models.Turno.estado_turno_empresa)).filter(models.Turno.id == turno_id, models.Turno.usuario_id == user_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    exito = crud.agregar_turno_historial(db, turno, variables.LISTA_PARCIAL_DE_ESTADOS)

    if exito:
        # Mando el id para que el frontend lo elimine del front y lo pase a historial y así no tener que enviarle todos sus turnos de vuelta
        return {"turno_id": turno_id}
    else:
        raise HTTPException(status_code=400, detail="Debe cambiar el estado antes de mover al historial al turno")

# Cada 5 minutos el fornt pregunta por los estados de sus turnos
@router.get("/turnos/estados", response_model=list[schemas.TurnoEstadoOut])
def get_estados_turnos_usuario(current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    turnos = db.query(models.Turno).options(
        joinedload(models.Turno.estado_turno_usuario)).filter_by(usuario_id=current_user.id).all()

    turnos_estados = []
    for t in turnos:
        turnos_estados.append(schemas.TurnoEstadoOut(
            id=t.id,
            estado=t.estado_turno_usuario.estado))

    return turnos_estados



# ---------------- RECUPERAR CONTRASEÑA ---------------- #



# ---------------- FORGOT PASSWORD ---------------- #

# ---------------- VÍA CELULAR ---------------- #
'''
@router.post("/forgot_password")
def forgot_password(solicitud: schemas.ForgotPassword, db: Session = Depends(get_db)):

    # Buscar usuario
    usuario = db.query(models.Usuario).join(models.Telefono).filter(models.Telefono.numero == solicitud.numero).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese número.")
    
    if usuario.email != solicitud.email:
        raise HTTPException(status_code=404, detail=f"El usuario con ese número no está registrado con el email {solicitud.email}")
    
    # Generar OTP
    otp = mensajes.generar_otp()

    nuevo_otp = models.OTPCode(
        usuario_id=usuario.id,
        code=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=2))
    db.add(nuevo_otp)
    db.commit()
    
    if solicitud.forma == 'wpp':

        # Enviar WhatsApp
        respuesta = mensajes.enviar_otp_whatsapp(solicitud.numero, usuario.nombre, otp)

        return {"message": "Código enviado por WhatsApp", "info": respuesta}
    
    if solicitud.forma == 'sms':
        tel = mensajes.enviar_sms(solicitud.numero, f"Tu código de recuperación de contraseña es {otp}")
        if not tel:
            raise HTTPException(status_code=500, detail="No se pudo enviar el SMS")
        return {"message": "Mensaje enviado", "tel": tel}
'''

# ---------------- VÍA EMAIL ---------------- #
@router.post("/forgot_password_email")
def forgot_password_email(solicitud: schemas.ForgotPasswordEmail, db: Session = Depends(get_db)):

    try:
        token = autenticacion.generate_password_reset_token(db, solicitud.email)
        mensajes.send_reset_email(solicitud.email, token)
    except ValueError:
        pass # No revelamos si el email existe o no

    return {"message": "Revisá tu correo para resetear la contraseña."}



# ---------------- RESET PASSWORD ---------------- #

# ---------------- VÍA CELULAR ---------------- #
'''
@router.post("/reset_password")
def reset_password(data: schemas.ResetPassword, db: Session = Depends(get_db)):

    usuario = db.query(models.Usuario).join(models.Telefono).filter(models.Telefono.numero == data.numero).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    otp_entry = db.query(models.OTPCode).filter(
        models.OTPCode.usuario_id == usuario.id,
        models.OTPCode.code == data.otp,
        models.OTPCode.used == False,
        models.OTPCode.expires_at > datetime.utcnow()).first()

    if not otp_entry:
        raise HTTPException(status_code=400, detail="OTP inválido o expirado.")

    #Actualizar contraseña
    usuario.hashed_password = autenticacion.get_password_hash(data.new_password)

    # Marcar OTP como usado
    otp_entry.used = True

    db.commit()

    return {"message": "Contraseña actualizada correctamente."}
'''

# ---------------- VÍA EMAIL ---------------- #
@router.post("/reset_password_email")
def reset_password_email(data: schemas.ResetPasswordEmail, db: Session = Depends(get_db)):

    try:
        autenticacion.reset_password(db, data.token, data.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Contraseña actualizada correctamente."}