'''
Este módulo es para la sección cliente del usuario
'''
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, constantes, exceptions, config, autenticacion, timezone
from core.database import get_db
from crud import common as crud_common
from crud import usuario as crud_usuario
from schemas import common as schemas_common
from schemas import usuario as schemas_usuario
from mappers import usuario as mappers_usuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
# APIRouter() crea un router, que es como una mini “sub-aplicación” dentro de FastAPI.
# prefix="/usuarios" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Usuarios"] sirve para organizar la documentación automática de Swagger (/docs).

# Crear usuario
# {"message": "Para validar su registro, le hemos enviamos un correo a su casilla con un enlace para verificar su cuenta"}
@router.post("/", status_code=201) # @router.post("/usuarios/") indica que esta función responde a POST en /usuarios/.
def create_usuario(user: schemas_usuario.UserCreate, response: Response, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario en la base de datos (registro).
    - Verifica que el email no esté ya registrado.
    - Hashea la contraseña antes de guardar.
    - Devuelve el OK en caso de éxito.
    """
    usuario = crud_usuario.create_usuario(db, user)

    if usuario and usuario.email_verificado:
        return {}

    # Enviar el mail
    limite_no_sobrepasado = crud_common.check_email_rate_limit(db, usuario.email, "REGISTER")

    if limite_no_sobrepasado:

        token = autenticacion.create_email_token(
            data={"sub": usuario.id},
            expires_delta=timedelta(hours=config.VERIFY_EMAIL_TOKEN_EXPIRE_HOURS)
        )

        try:
            mensajes.send_verification_email(usuario.email, token)
        except exceptions.EmailSendFailedError:
            pass # no revelamos si el email se mandó o no

    return {}

# {"message": "Correo verificado con éxito"}
@router.get("/verificacion/email", status_code=204)
def verificacion_email_usuario(token: str, db: Session = Depends(get_db)):

    crud_common.verificacion_email(db, token)

@router.get("/me", response_model=schemas_usuario.UserLoginOut, status_code=200)
def me(current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):
    '''
    Esto es para que cuando el creat o login dé el OK, el navegador pida los datos del
    usuario para el HTML del panel del usuario.
    También se usa para que el usuario entre a su panel de una cuando abra la app o dominio y ya estaba logueado y 
    el navegador ya tiene la cookie y así el usuario no tiene que poner de vuelta la contraseña y el email.
    '''
    turnos = crud_usuario.get_turnos(db, current_user.id)
    
    us = mappers_usuario.user_login_out(current_user, turnos)

    return us

# Actualizar usuario (datos simples, telefonos y direcciones)
@router.patch("/me", response_model=schemas_usuario.UserUpdateOut, status_code=200)
def update_usuario(user_update: schemas_usuario.UserUpdateIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    user = crud_usuario.update(db, current_user, user_update)
    
    us = mappers_usuario.user_update_out(user)

    return us

@router.get("/mis_empresas", response_model=list[schemas_usuario.RolEmpresaOut], status_code=200)
def get_roles(current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    # Traer roles en empresas (roles es una lista de objetos Miembro_Empresa de SQAlchemy)
    roles = (
        db.query(models.Miembro_Empresa).options(
            joinedload(models.Miembro_Empresa.empresa).joinedload(models.Empresa.direccion)
        ).filter_by(usuario_id=current_user.id).all()
    )

    roles_empresas_out = [mappers_usuario.rol_empresa_out(rol) for rol in roles]

    return roles_empresas_out

# Usuario reserva turno
@router.post("/turnos", response_model=schemas_usuario.TurnoUserOut, status_code=201)
def reservar_turno(reserva: schemas_usuario.ReservaTurnoOpcionesIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    turno = crud_usuario.reservar_turno(db, current_user.id, reserva, current_user.recordatorio_minutos_antes)

    turno_out = mappers_usuario.turno_user_out(turno)

    return turno_out

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.patch("/turnos", response_model=schemas_usuario.TurnoUserOut, status_code=200)
def update_turno_usuario(turno_update: schemas_common.TurnoUpdateIn, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    turno_modificado = crud_usuario.update_turno(db, current_user, turno_update)
    
    turno_out = mappers_usuario.turno_user_out(turno_modificado)

    return turno_out

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
@router.delete("/turnos/{turno_id}", status_code=204)
def delete_turno_usuario(turno_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_usuario.delete_turno(db, current_user.id, turno_id, constantes.LISTA_PARCIAL_DE_ESTADOS)

# Cada 5 minutos el front pregunta por los estados de sus turnos
@router.get("/turnos/estados", response_model=list[schemas_common.TurnoEstadoOut], status_code=200)
def get_estados_turnos_usuario(current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    turnos = crud_usuario.get_estados_turnos(db, current_user.id)

    turnos_estados = [mappers_usuario.turno_estado_out(turno) for turno in turnos]

    return turnos_estados

# Devuelve todos los turnos que el usuario ya completó (tabla Historial) (el primero devuelto será el más reciente)
@router.get("/historial", response_model=schemas_usuario.HistorialUserOut, status_code=200)
def get_historial_usuario(current_user: models.Usuario = Depends(autenticacion.get_current_user), 
    db: Session = Depends(get_db), before: Optional[datetime] = Query(None)):
    
    fecha_hora_ultima = timezone.to_naive_utc(before) if before else datetime.max # si el before fue pasado, se toma, y si no, se toma datetime.max

    historial, ultimo_cursor = crud_usuario.get_historial(
        db, current_user.id, fecha_hora_ultima=fecha_hora_ultima)
    
    historial_out = [mappers_usuario.turno_historial_user(h) for h in historial]
    
    respuesta = schemas_usuario.HistorialUserOut(
        historial=historial_out, # historial_out es una lista de objetos de clase TurnoHistorialUser de Pydantic
        ultimo_cursor=timezone.ensure_utc(ultimo_cursor)) # ultimo_cursor volverá si el usuario pide más historial
    
    return respuesta

# Devuelve lista de empresas (sin duplicados) con coincidencia parcial de nombre y/o rubros
# haciendo, por ejemplo, GET /usuarios/search/empresa?query=peluq
@router.get("/empresas/search", response_model=list[schemas_usuario.EmpresaOut], status_code=200)
def get_empresas(query: str, lat: float, lng: float, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    empresas = crud_usuario.get_empresas(db, query, lat, lng) # empresas es una lista de objetos de clase Empresa de SQLAlchemy

    resultados = [mappers_usuario.empresa_out(empresa) for empresa in empresas]

    return resultados

# Se envía al hacer click en la empresa
@router.get("/empresas/{empresa_id}/servicios", response_model=list[schemas_usuario.ServicioConTurnosOut], status_code=200)
def get_servicios_de_empresa(empresa_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    servicios, turnos = crud_usuario.get_servicios_de_empresa(db, current_user.id, empresa_id)

    servicios_out = mappers_usuario.servicio_con_turnos_out(servicios, turnos)

    return servicios_out

@router.post("/empresas/{empresa_id}/favoritos", response_model=schemas_usuario.EmpresaOut, status_code=201)
def add_favorito(empresa_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    empresa = crud_usuario.add_favorito(db, current_user.id, empresa_id)
    
    empresa_out = mappers_usuario.empresa_out(empresa)

    return empresa_out

@router.delete("/empresas/{empresa_id}/favoritos", status_code=204)
def delete_favorito(empresa_id: int, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_usuario.delete_favorito(db, current_user.id, empresa_id)

# {"message": "Calificación guardada con éxito"}
@router.post("/empresas/{empresa_id}/calificacion", status_code=201)
def calificar_empresa(empresa_id: int, calificacion_recibida: schemas_usuario.Calificacion, 
    current_user: models.Usuario = Depends(autenticacion.get_current_user), db: Session = Depends(get_db)):

    crud_usuario.agregar_calificacion(db, empresa_id, calificacion_recibida.valor)
    
    return {}