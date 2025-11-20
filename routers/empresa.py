from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Response, HTTPException, status # Depends se usa para declarar dependencias en FastAPI (por ejemplo, obtener la sesión de base de datos).
from sqlalchemy.orm import Session, joinedload, selectinload # Session de SQLAlchemy, representa una sesión de base de datos.

from core import models, schemas, crud, autenticacion, auxiliares, variables
from core.database import get_db

router = APIRouter(prefix="/empresas", tags=["Empresas"])
# APIRouter() crea un router, que es como un mini “sub-aplicación” dentro de FastAPI.
# prefix="/empresas" agrega un prefijo automático a todos los endpoints que se declaren dentro del router (este módulo).
# tags=["Empresas"] sirve para organizar la documentación automática de Swagger (/docs).

# Crear empresa
@router.post("/") # @router.post("/empresas/") indica que esta función responde a POST en /empresas/.
def create_empresa(empresa: schemas.EmpresaCreate, response: Response, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    try:
        db_empresa = crud.create_empresa(db, empresa) # Devuelve un objeto de clase Empresa de SQLAlchemy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    crud.asignar_rol(db, current_user.id, db_empresa.id, 'propietario')

    return {"msg": "Empresa creada exitosamente. Cierre sesión en su cuenta y vuelva a entrar para poder visualizar el panel de la empresa creada."}

@router.get("/{empresa_id}/panel", response_model=schemas.EmpresaPanelOut)
def acceder_empresa(empresa_id: int, current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verifico que el usuario que mandó la petición pertenezca a la empresa y devuelvo su rol
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)
    
    empresa = crud.get_empresa(db, empresa_id) # empresa es un objeto de clase Empresa (con sus relationships) de SQLAlchemy

    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    emp = auxiliares.convertir_orm_pydantic_empresa(empresa, current_user_rol)

    return emp # emp es un objeto de clase EmpresaPanelOut de Pydantic

# Actualizar empresa (datos simples, telefonos y dirección)
@router.put("/{empresa_id}", response_model=schemas.EmpresaPanelOut)
def update_empresa(empresa_id: int, empresa_update: schemas.EmpresaUpdate, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    if current_user_rol == 'empleado':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Los empleados no pueden modificar datos.")
    
    db_emp = crud.update_empresa(db, empresa_id, empresa_update)
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    empresa = crud.get_empresa(db, empresa_id) # empresa ahora es un objeto de clase Empresa (con sus relationships actualizadas) de SQLAlchemy
    
    emp = auxiliares.convertir_orm_pydantic_empresa(empresa, current_user_rol)

    return emp # emp es un objeto de clase EmpresaPanelOut de Pydantic

@router.put("/{empresa_id}/servicios", response_model=schemas.EmpresaPanelOut)
def update_servicios_empresa(
    empresa_id: int,
    servicios_update: schemas.ServiciosUpdateIn,
    current_user: models.Usuario = Depends(crud.get_current_user),
    db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    if current_user_rol == 'empleado':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Los empleados no pueden modificar datos.")
    
    db_emp = crud.update_servicios_empresa(db, empresa_id, servicios_update)
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    empresa = crud.get_empresa(db, empresa_id) # empresa ahora es un objeto de clase Empresa (con sus relationships actualizadas) de SQLAlchemy
    
    emp = auxiliares.convertir_orm_pydantic_empresa(empresa, current_user_rol)

    return emp # emp es un objeto de clase EmpresaPanelOut de Pydantic

@router.delete("/{empresa_id}/servicios", response_model=schemas.EmpresaPanelOut)
def eliminar_servicios_empresa(
    empresa_id: int,
    servicios_delete: schemas.ServiciosDeleteIn,
    current_user: models.Usuario = Depends(crud.get_current_user),
    db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    if current_user_rol == 'empleado':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Los empleados no pueden modificar datos.")
    
    db_emp = crud.eliminar_servicios_empresa(db, empresa_id, servicios_delete)
    if not db_emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    empresa = crud.get_empresa(db, empresa_id) # empresa ahora es un objeto de clase Empresa (con sus relationships actualizadas) de SQLAlchemy
    
    emp = auxiliares.convertir_orm_pydantic_empresa(empresa, current_user_rol)

    return emp # emp es un objeto de clase EmpresaPanelOut de Pydantic

# Devuelve todos los turnos que la empresa ya completó (tabla Historial) (el primero devuelto será el más reciente)
@router.get("/{empresa_id}/historial", response_model=schemas.HistorialEmpresaResponse)
def get_historial_turnos(empresa_id: int, current_user: models.Usuario = Depends(crud.get_current_user), 
    db: Session = Depends(get_db), before: Optional[datetime] = None):
    
    # Verifico que el usuario que mandó la petición pertenezca a la empresa
    crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    f_h_ultima = before or datetime.max # si el before fue pasado, se toma, y si no, se toma datetime.max

    historial, ultimo_cursor = crud.get_historial_turnos(
        db, empresa_id, fecha_hora_ultima=f_h_ultima, user=False) # historial es una lista de objetos de clase Historial de SQLAlchemy

    if not historial:
        raise HTTPException(status_code=404, detail="No hay historial de turnos")
    
    resultados = []
    for h in historial:
        resultados.append(schemas.HistorialEmpresaOut(
            usuario_dni=h.usuario.dni,
            usuario_apellido=h.usuario.apellido,
            usuario_nombre=h.usuario.nombre,
            fecha_hora=h.fecha_hora,
            nombre_de_servicio=h.nombre_de_servicio,
            duracion=h.duracion,
            precio=h.precio,
            aclaracion_de_servicio=h.aclaracion_de_servicio,
            profesional_dni=h.profesional.dni if h.profesional else None,
            profesional_apellido=h.profesional.apellido if h.profesional else None,
            profesional_nombre=h.profesional.nombre if h.profesional else None,
            estado_turno=h.estado_turno_usuario.estado))
    
    respuesta = schemas.HistorialEmpresaResponse(
        historial=resultados, # resultados es una lista de objetos de clase HistoriaEmpresalOut de Pydantic
        ultimo_cursor=ultimo_cursor) # ultimo_cursor volverá si el usuario pide más historial
    
    return respuesta

# Modifica el estado de un turno de la tabla Turno y devuelve el turno con el estado modificado
@router.put("/{empresa_id}/turnos/", response_model=schemas.TurnoEmpresaOut)
def modificar_turno_empresa(
    empresa_id: int, 
    turno_update: schemas.TurnoUpdate, 
    current_user: models.Usuario = Depends(crud.get_current_user), 
    db: Session = Depends(get_db)):

    # Verifico que el usuario que mandó la petición pertenezca a la empresa
    crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    turno = db.query(models.Turno).filter(models.Turno.id == turno_update.id, models.Turno.empresa_id == empresa_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    turno_modificado = crud.modificar_turno(db, turno, turno_update.estado_turno, user=False)

    # Convertir el objeto SQLAlchemy a Pydantic
    turno_out = schemas.TurnoEmpresaOut(
        id=turno_modificado.id,
        usuario_dni=turno_modificado.usuario.dni,
        usuario_apellido=turno_modificado.usuario.apellido,
        usuario_nombre=turno_modificado.usuario.nombre,
        fecha_hora=turno_modificado.fecha_hora,
        nombre_de_servicio=turno_modificado.nombre_de_servicio,
        duracion=turno_modificado.duracion,
        precio=turno_modificado.precio,
        aclaracion_de_servicio=turno_modificado.aclaracion_de_servicio,
        profesional_dni=turno_modificado.profesional.dni if turno_modificado.profesional else None,
        profesional_apellido=turno_modificado.profesional.apellido if turno_modificado.profesional else None,
        profesional_nombre=turno_modificado.profesional.nombre if turno_modificado.profesional else None,
        estado_turno=turno_modificado.estado_turno_usuario.estado)

    return turno_out

# Pasa un turno a la tabla Historial en caso de que lo haya pedido el usuario o la empresa y lo elimina en caso de que lo hayan ya pedido los 2
@router.delete("/{empresa_id}/turnos/{turno_id}")
def agregar_turno_historial_empresa(empresa_id: int, turno_id: int, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verifico que el usuario que mandó la petición pertenezca a la empresa
    crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    turno = db.query(models.Turno).options(
            joinedload(models.Turno.usuario),
            joinedload(models.Turno.profesional),
            joinedload(models.Turno.empresa).joinedload(models.Empresa.direccion),
            joinedload(models.Turno.estado_turno_usuario),
            joinedload(models.Turno.estado_turno_empresa)).filter(models.Turno.id == turno_id, models.Turno.empresa_id == empresa_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    exito = crud.agregar_turno_historial(db, turno, variables.LISTA_PARCIAL_DE_ESTADOS, user=False)

    if exito:
        # Mando el id para que el frontend lo elimine del front y lo pase a historial y así no tener que enviarle todos sus turnos de vuelta
        return {"msg": "Turno movido al historial correctamente", "turno_id": turno_id}
    else:
        raise HTTPException(status_code=400, detail="Debe cambiar el estado antes de mover al historial al turno")

@router.post("/{empresa_id}/invitar_empleado")
def invitar_empleado(
    empresa_id: int,
    invitacion: schemas.InvitacionEmpleadoIn,
    current_user: models.Usuario = Depends(crud.get_current_user),
    db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    roles_superiores = ["propietario", "gerente"]

    if current_user_rol == 'gerente' and invitacion.rol in roles_superiores:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés permisos para asignar este rol.")
    if current_user_rol == 'empleado':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Los empleados no pueden asignar roles.")

    # Buscar usuario por email
    usuario = db.query(models.Usuario).filter(models.Usuario.email == invitacion.usuario_email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Crear token JWT usando create_access_token
    token = autenticacion.create_access_token(
        data={"usuario_id": usuario.id, "empresa_id": empresa_id, "rol": invitacion.rol},
        expires_delta=timedelta(minutes=variables.ACCESS_TOKEN_EXPIRE_MINUTES))

    # Enviar mail
    send_invite_email(usuario.email, token, empresa_nombre=db.query(models.Empresa).get(empresa_id).nombre, rol=invitacion.rol)

    return {"message": f"Invitación enviada a {usuario_email} para el rol {invitacion.rol}"}

@router.post("/aceptar_rol")
def aceptar_rol(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, variables.SECRET_KEY, algorithms=[variables.ALGORITHM])
        usuario_id = payload.get("usuario_id")
        empresa_id = payload.get("empresa_id")
        rol = payload.get("rol")
    except:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    # Verificar si ya es miembro
    existe = db.query(models.Miembro_Empresa).filter_by(usuario_id=usuario_id, empresa_id=empresa_id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya sos miembro de esta empresa")

    nuevo_miembro = models.Miembro_Empresa(usuario_id=usuario_id, empresa_id=empresa_id, rol=rol)
    db.add(nuevo_miembro)
    db.commit()

    return {"message": "OK"}

@router.put("/{empresa_id}/modificar_rol")
def modificar_rol(empresa_id: int, datos: schemas.ModificarRolIn, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)
    if current_user_rol != 'propietario':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés permisos para modificar roles.")
    
    # Traer el objeto de clase Miembro_Empresa al que se le modificará el rol
    miembro_empresa = db.query(models.Miembro_Empresa).filter_by(usuario_id=datos.usuario_id, empresa_id=empresa_id).options(
        joinedload(models.Miembro_Empresa.usuario)).first()
    if not miembro_empresa:
        raise HTTPException(status_code=404, detail="Este usuario no pertenece a la empresa")
    
    # Modificar el rol
    miembro_empresa.rol = datos.nuevo_rol
    db.commit()

    return {"message": f"Rol de {miembro_empresa.usuario.apellido}, {miembro_empresa.usuario.nombre} modificado a {datos.nuevo_rol}"}

@router.delete("/{empresa_id}/eliminar_miembro")
def eliminar_miembro(empresa_id: int, datos: schemas.EliminarMiembroIn, 
    current_user: models.Usuario = Depends(crud.get_current_user), db: Session = Depends(get_db)):

    # Verificar que current_user sea propietario o gerente
    current_user_rol = crud.verificar_rol_en_empresa(db, current_user.id, empresa_id)

    # Traer el objeto de clase Miembro_Empresa al que se le modificará el rol
    miembro_empresa = db.query(models.Miembro_Empresa).filter_by(usuario_id=datos.usuario_id, empresa_id=empresa_id).options(
        joinedload(models.Miembro_Empresa.usuario)).first()
    if not miembro_empresa:
        raise HTTPException(status_code=404, detail="Este usuario no pertenece a la empresa")

    roles_superiores = ["propietario", "gerente"]

    if current_user_rol == 'gerente' and miembro_empresa.rol in roles_superiores:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés permisos para eliminar a este miembro.")
    if current_user_rol == 'empleado':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Los empleados no pueden eliminar miembros.")
    
    # Modificar el rol
    db.delete(miembro_empresa)
    db.commit()

    return {"message": f"{miembro_empresa.usuario.apellido}, {miembro_empresa.usuario.nombre} fue eliminado correctamente de esta empresa"}
