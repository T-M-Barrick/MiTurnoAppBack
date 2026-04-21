import time

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from core import models, autenticacion, auxiliares
from core.database import get_db
from crud import invitaciones as crud_invitaciones
from services import auth as services_auth
from schemas import invitaciones as schemas_invitaciones
from mappers import invitaciones as mappers_invitaciones

router = APIRouter(prefix="/invitaciones", tags=["Invitaciones"])

@router.post("/", status_code=204)
def invitar_empleado(
    invitacion: schemas_invitaciones.InvitacionEmpleadoIn,
    background_tasks: BackgroundTasks, # clave para el tiempo constante
    current_user: models.Usuario = Depends(autenticacion.get_current_user),
    db: Session = Depends(get_db),
) -> None:

    start_time = time.time() # iniciamos el cronómetro
    tiempo_objetivo = 0.06 # el objetivo es siempre tardar 60ms

    usuario_email = invitacion.usuario_email
    rol = invitacion.rol
    empresa_id = invitacion.empresa_id
    sucursal_id = invitacion.sucursal_id

    usuario, entidad, cantidad_sucursales = crud_invitaciones.invitar_empleado(
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
            cantidad_sucursales,
            rol,
        )
    
    # NORMALIZACIÓN TOTAL:
    # No importa si entramos al 'if usuario' o al 'if not usuario',
    # al final calculamos cuánto tiempo pasó y dormimos el resto.
    tiempo_transcurrido = time.time() - start_time
    if tiempo_transcurrido < tiempo_objetivo:
        time.sleep(tiempo_objetivo - tiempo_transcurrido)

@router.post("/aceptar", response_model=schemas_invitaciones.InvitacionAceptadaOut, status_code=201)
def aceptar_invitacion(
    token: str = Query(..., min_length=20, max_length=1000),
    db: Session = Depends(get_db),
) -> schemas_invitaciones.InvitacionAceptadaOut:

    entidad_nombre, nuevo_rol, cantidad_sucursales = crud_invitaciones.aceptar_invitacion(db, token)
    
    return mappers_invitaciones.invitacion_aceptada_out(entidad_nombre, nuevo_rol, cantidad_sucursales)