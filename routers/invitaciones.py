from datetime import datetime, timedelta
import time

from fastapi import APIRouter, Depends, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload, selectinload

from core import models, autenticacion, auxiliares, constantes, mensajes
from core.database import get_db
from crud import common as crud_common
from crud import invitaciones as crud_invitaciones
from services import auth as services_auth
from schemas import invitaciones as schemas_invitaciones
from mappers import invitaciones as mappers_invitaciones

router = APIRouter(prefix="/invitaciones", tags=["Invitaciones"])

# {"message": f"Invitación enviada a {usuario_email} para el rol {rol}"}
@router.post("/", status_code=204)
def invitar_empleado(
    invitacion: schemas_invitaciones.InvitacionEmpleadoIn,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
):

    start_time = time.time() # iniciamos el cronómetro
    tiempo_objetivo = 0.06 # el objetivo es siempre tardar 60ms

    usuario_email = invitacion.usuario_email
    rol = invitacion.rol
    empresa_id = invitacion.empresa_id
    sucursal_id = invitacion.sucursal_id

    usuario, entidad = crud_invitaciones.invitar_empleado(
        db, empresa_id, sucursal_id, current_user.id, usuario_email, rol,
    )

    if usuario:

        if sucursal_id:
            sucursal = entidad
            entidad_nombre = auxiliares.nombre_empresa(sucursal.empresa.nombre, sucursal.nombre)
        else:
            empresa = entidad
            entidad_nombre = empresa.nombre
        
        if not entidad_nombre:
            raise ValueError("La variable entidad_nombre de la función invitar_empleado del router invitaciones es None")

        # Agendamos la tarea y respondemos 204 ya.
        background_tasks.add_task(
            services_auth.background_invitar_empleado,
            usuario.email,
            usuario.id,
            entidad_nombre,
            empresa_id,
            sucursal_id,
            rol,
        )
    
    # NORMALIZACIÓN TOTAL:
    # No importa si entramos al 'if usuario' o al 'if not usuario',
    # al final calculamos cuánto tiempo pasó y dormimos el resto.
    tiempo_transcurrido = time.time() - start_time
    if tiempo_transcurrido < tiempo_objetivo:
        time.sleep(tiempo_objetivo - tiempo_transcurrido)

    '''
    # Volver a poner si no se logra lo del mail
    ###################################
    from mappers import empresa as mappers_empresa

    email_normalizado = models.normalizar_email(usuario_email)

    nuevo_miembro = db.query(models.Usuario).filter_by(email_normalizado=email_normalizado).first()

    miembro = db.query(models.Miembro_Empresa).options(
        joinedload(models.Miembro_Empresa.usuario)).filter_by(
        usuario_id=nuevo_miembro.id, empresa_id=empresa_id).first()
    
    miembro_out = mappers_empresa.miembro_out(miembro)

    return miembro_out
    ###################################
    '''

# {"message": f"¡¡Fuiste incorporado exitosamente como {rol} en {nombre}!!"}
@router.post("/aceptar", response_model=schemas_invitaciones.InvitacionAceptadaOut, status_code=201)
def aceptar_invitacion(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
):

    entidad_nombre, nuevo_rol = crud_invitaciones.aceptar_invitacion(db, token)
    
    return mappers_invitaciones.invitacion_aceptada_out(entidad_nombre, nuevo_rol)