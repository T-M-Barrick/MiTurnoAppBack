from datetime import datetime, timedelta

from core.database import SessionLocal
from core.schemas import UserLoginOut, DireccionOut, EmpresaOut, TurnoOut
from core.models import Turno, Blacklist
from core.variables import DIAS_NOMBRES

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioLoginOut o UsuarioUpdateOut de Pydantic (y agrega turnos si tiene)
def convertir_orm_pydantic_usuario(user, update=False, turnos_del_usuario=[]):

    if not update:
        us = schemas.UserLoginOut(
            id=user.id,
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,

            telefonos=[[t.id, t.numero] for t in user.telefonos],

            direcciones=[schemas.DireccionOut(
                id=d.id,
                domicilio=d.domicilio,
                lat=d.lat,
                lng=d.lng,
                aclaracion=d.aclaracion) for d in user.direcciones],
            
            favoritos=[schemas.EmpresaOut(
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
                    aclaracion=e.direccion.aclaracion),
                servicios=list({s.nombre for s in e.servicios}) # Evita duplicados
            ) for e in user.favoritos],

            turnos=[schemas.TurnoOut(
                id=turn.id,
                empresa=turn.empresa.nombre,
                direccion=schemas.DireccionOut(
                    id=turn.empresa.direccion.id,
                    domicilio=turn.empresa.direccion.domicilio,
                    lat=turn.empresa.direccion.lat,
                    lng=turn.empresa.direccion.lng,
                    aclaracion=turn.empresa.direccion.aclaracion),
                fecha_hora=turn.fecha_hora,
                nombre_de_servicio=turn.nombre_de_servicio,
                duracion=turn.duracion,
                precio=turn.precio,
                aclaracion_de_servicio=turn.aclaracion_de_servicio,
                profesional_dni=turn.profesional.dni if turn.profesional else None,
                profesional_apellido=turn.profesional.apellido if turn.profesional else None,
                profesional_nombre=turn.profesional.nombre if turn.profesional else None,
                estado_turno=turn.estado_turno_usuario.estado
            ) for turn in turnos_del_usuario]
        )   
    if update:
        us = schemas.UserUpdateOut(
            id=user.id,
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,

            telefonos=[[t.id, t.numero] for t in user.telefonos],

            direcciones=[schemas.DireccionOut(
                id=d.id,
                domicilio=d.domicilio,
                lat=d.lat,
                lng=d.lng,
                aclaracion=d.aclaracion) for d in user.direcciones],
            
            favoritos=[schemas.EmpresaOut(
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
                    aclaracion=e.direccion.aclaracion),
                servicios=list({s.nombre for s in e.servicios}) # Evita duplicados
            ) for e in user.favoritos]
        )
        
    return us # us será un objeto de clase UsuarioLoginOut o de la clase UsuarioUpdateOut de Pydantic

# Convierte un objeto de la clase Empresa de SQLAlchemy en uno de clase EmpresaPanelOut de Pydantic
def convertir_orm_pydantic_empresa(empresa, miembro_rol):

    # Armar listas anidadas según schemas
    telefonos = [[t.id, t.numero] for t in empresa.telefonos]

    direccion_out = schemas.DireccionOut(
        id=empresa.direccion.id,
        domicilio=empresa.direccion.domicilio,
        lat=empresa.direccion.lat,
        lng=empresa.direccion.lng,
        aclaracion=empresa.direccion.aclaracion)
    
    servicios_out = []
    for s in empresa.servicios:
        profesional = s.profesional
        usuario = profesional.usuario if profesional else None

        servicios_out.append(
            schemas.ServicioOut(
                id=s.id,
                nombre=s.nombre,
                duracion=s.duracion,
                precio=s.precio,
                aclaracion=s.aclaracion,
                profesional_id=s.miembro_empresa_id,
                profesional_dni=usuario.dni if usuario else None,
                profesional_apellido=usuario.apellido if usuario else None,
                profesional_nombre=usuario.nombre if usuario else None,
                disponibilidades=[
                    schemas.DisponibilidadOut(
                        id=sd.disponibilidad.id,
                        dia=sd.disponibilidad.dia,
                        hora=sd.disponibilidad.hora,
                        cant_turnos_max=sd.cant_turnos_max) for sd in s.ser_disps]
            )
        )

    turnos = crud.get_turnos(db, empresa_id, user=False)
    turnos_out = [schemas.TurnoEmpresaOut(
        id=t.id,
        usuario_dni=t.usuario.dni,
        usuario_apellido=t.usuario.apellido,
        usuario_nombre=t.usuario.nombre,
        fecha_hora=t.fecha_hora,
        nombre_de_servicio=t.nombre_de_servicio,
        duracion=t.duracion,
        precio=t.precio,
        aclaracion_de_servicio=t.aclaracion_de_servicio,
        profesional_dni=t.profesional.dni if t.profesional else None,
        profesional_apellido=t.profesional.apellido if t.profesional else None,
        profesional_nombre=t.profesional.nombre if t.profesional else None,
        estado_turno=t.estado_turno_empresa.estado) for t in turnos]

    miembros_out = [schemas.UserOut(
        id=m.usuario.id,
        dni=m.usuario.dni,
        apellido=m.usuario.apellido,
        nombre=m.usuario.nombre,
        email=m.usuario.email,
        rol=m.rol) for m in empresa.miembros]

    empresa_out = schemas.EmpresaPanelOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        calificacion=empresa.calificacion,
        telefonos=telefonos,
        direccion=direccion_out,
        servicios=servicios_out,
        turnos=turnos_out,
        miembros=miembros_out,
        rol=miembro_rol)

    return empresa_out

def extraer_dia_y_hora(fecha_hora: datetime):
    """
    Convierte un datetime en día de la semana y hora
    """
    dias_nombres = DIAS_NOMBRES 
    dia_semana = fecha_hora.weekday() # 0 = lunes, 6 = domingo

    nombre_dia = dias_nombres[dia_semana]
    hora = fecha_hora.time() # hora del turno
    
    return nombre_dia, hora

def limpiar_tokens_expirados():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        db.query(Blacklist).filter(Blacklist.expires_at < now).delete()
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

'''
from core.crud import eliminar_turno

def limpiar_turnos_vencidos():
    db = SessionLocal()
    try:
        hace_7_dias = datetime.now() - timedelta(days=7)
        turnos_vencidos = db.query(models.Turno).filter(models.Turno.fecha_hora < hace_7_dias).all()
        for turno in turnos_vencidos:
            eliminar_turno(db, turno)
    except Exception as e:
        print(f"Error al limpiar turnos: {e}")  # o usar logging
    finally:
        db.close()
'''