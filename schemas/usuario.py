from datetime import datetime, date, time

from pydantic import BaseModel, EmailStr, Field, conint, condecimal, constr, conlist, field_validator, model_validator, root_validator

from schemas.common import (Telefono, TelefonoConID, DireccionCreate,
    DireccionOut, DireccionUpdateIn, DisponibilidadServicio, EstadoTurno, RolEmpresa, RolSucursal)
from core.timezone import validate_aware_utc

class UserCreate(BaseModel):
    dni: constr(regex=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    password: constr(min_length=8, max_length=128, strip_whitespace=True)
    telefonos: conlist(Telefono, min_length=1)
    direcciones: conlist(DireccionCreate, min_length=1)

    model_config = {"from_attributes": True}

class EmpresaOut(BaseModel):
    id: conint(ge=1)
    cuit: constr(regex=r"^[0-9]{11}$")
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    rubro: constr(min_length=1, max_length=100) | None
    rubro2: constr(min_length=1, max_length=100) | None
    calificacion: condecimal(ge=0, le=10, max_digits=4, decimal_places=2) | None
    telefonos: list[Telefono]
    direccion: DireccionOut
    logo_url: constr(min_length=1, max_length=255) | None

    model_config = {"from_attributes": True}

class TurnoUserOut(BaseModel):
    id: conint(ge=1)
    empresa_id: conint(ge=1)
    empresa: constr(min_length=1, max_length=50)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    direccion: DireccionOut
    fecha_hora: datetime # debe salir como aware UTC
    nombre_de_servicio: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(regex=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    estado_turno: EstadoTurno
    recordatorio: conint(ge=0, le=1410, multiple_of=30) | None

    @field_validator("fecha_hora")
    def validar_fecha_hora_utc(value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = {"from_attributes": True}

class UserLoginOut(BaseModel):
    id: conint(ge=1)
    dni: constr(regex=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    recordatorio: conint(ge=0, le=1410, multiple_of=30) | None
    telefonos: conlist(TelefonoConID, min_length=1)
    direcciones: conlist(DireccionOut, min_length=1)
    favoritos: list[EmpresaOut]
    turnos: list[TurnoUserOut]

    model_config = {"from_attributes": True}

class UserUpdateIn(BaseModel):
    '''
    Que en un campo se envíe None o no se envíe el campo directamente, significa que no se actualiza ese campo.
    No significa, por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL o se borre.
    '''
    dni: constr(regex=r"^[0-9]{6,8}$") | None = None
    apellido: constr(min_length=1, max_length=50) | None = None
    nombre: constr(min_length=1, max_length=50) | None = None
    recordatorio: conint(ge=0, le=1410, multiple_of=30) | None = None
    telefonos: conlist(TelefonoConID, min_length=1) | None = None 
    direcciones: conlist(DireccionUpdateIn, min_length=1) | None = None

    @root_validator(mode="before")
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        campos_permitidos_null = ["recordatorio"]

        for field, value in values.items():
            if field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema UserUpdateIn no puede enviarse como null')

        return values

    model_config = {"from_attributes": True}

class UserUpdateOut(BaseModel):
    id: conint(ge=1)
    dni: constr(regex=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    recordatorio: conint(ge=0, le=1410, multiple_of=30) | None
    telefonos: conlist(TelefonoConID, min_length=1)
    direcciones: conlist(DireccionOut, min_length=1)

    model_config = {"from_attributes": True}

class RolEmpresaOut(BaseModel):
    rol: RolEmpresa
    empresa_id: conint(ge=1)
    nombre_empresa: constr(min_length=1, max_length=50)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    
    model_config = {"from_attributes": True}

class TarjetaSucursalOut(BaseModel):
    rol: RolEmpresa
    sucursal_id: conint(ge=1)
    nombre_sucursal: constr(min_length=1, max_length=50)
    direccion: DireccionOut
    
    model_config = {"from_attributes": True}

class RolSucursalOut(BaseModel):
    rol: RolSucursal
    sucursal_id: conint(ge=1)
    nombre_sucursal: constr(min_length=1, max_length=50)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    direccion: DireccionOut
    
    model_config = {"from_attributes": True}

class ReservaTurnoIn(BaseModel):
    empresa_id: conint(ge=1)
    servicio_id: conint(ge=1)
    fecha_hora: datetime # debe llegar como aware UTC

    @field_validator("fecha_hora")
    def validar_fecha_hora_utc(value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = {"from_attributes": True}

class ReservaTurnoOpcionesIn(BaseModel):
    opciones: conlist(ReservaTurnoIn, min_length=1)

    @model_validator(mode="after")
    def validar_empresa_id_y_fecha_hora(cls, values):
        opciones = values.opciones

        # Tomo el primer elemento como referencia
        empresa_id_ref = opciones[0].empresa_id
        fecha_hora_ref = opciones[0].fecha_hora

        for opt in opciones:
            if opt.empresa_id != empresa_id_ref:
                raise ValueError("Todos los reservas deben tener el mismo empresa_id")
            if opt.fecha_hora != fecha_hora_ref:
                raise ValueError("Todos los reservas deben tener el mismo fecha_hora")
        return values

    model_config = {"from_attributes": True}

class TurnoHistorialUser(BaseModel):
    empresa: constr(min_length=1, max_length=50)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    fecha_hora: datetime # debe salir como aware UTC
    nombre_de_servicio: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(regex=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    estado_turno: EstadoTurno

    @field_validator("fecha_hora")
    def validar_fecha_hora_utc(value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = {"from_attributes": True}

class HistorialUserOut(BaseModel):
    historial: list[TurnoHistorialUser]
    ultimo_cursor: datetime | None

    @field_validator("ultimo_cursor")
    def validar_fecha_hora_utc(value: datetime | None) -> datetime | None:
        return validate_aware_utc(value) if value else None

    model_config = {"from_attributes": True}

class TurnoActualDelServicio(BaseModel):
    id: conint(ge=1)
    fecha_hora: datetime # debe salir como aware UTC
    duracion: conint(gt=0, multiple_of=5) # minutos

    @field_validator("fecha_hora")
    def validar_fecha_hora_utc(value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = {"from_attributes": True}

class ServicioConTurnosOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion: constr(min_length=1, max_length=255) | None
    profesional_id: conint(ge=2) | None # 1 no se permite porque significa que no tiene profesional y debe salir como None
    profesional_dni: constr(regex=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    dias_max_reserva: conint(ge=0) | None
    disponibilidades: list[DisponibilidadServicio]
    turnos_actuales: list[TurnoActualDelServicio]

    model_config = {"from_attributes": True}

class Calificacion(BaseModel):
    valor: conint(ge=0, le=10)  # solo permite enteros de 0 a 10

    model_config = {"from_attributes": True}

'''
Ejemplo de respuesta real de pydantic dentro de un validator (no envía un 500, sino que envía un 422):

{
  "detail": [
    {
      "loc": ["body", "telefonos"],
      "msg": "Debido a que un usuario no puede no tener ningún teléfono asociado...",
      "type": "value_error"
    }
  ]
}

No imprime traceback y no devuelve 500 pese al ValueError.
Pydantic aplasta todo con un 422 y le dice a FastAPI, que luego es el que arma la respuesta HTTP 422 y la envía.
'''