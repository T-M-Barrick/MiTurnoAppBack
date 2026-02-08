from datetime import datetime, date, time

from pydantic import BaseModel, EmailStr, Field, conint, condecimal, constr, conlist, field_validator, model_validator, root_validator

from schemas.common import (Telefono, TelefonoConID, DireccionCreate,
    DireccionOut, DireccionUpdateIn, DisponibilidadServicio, EstadoTurno, RolEmpresa, RolSucursal)
from core.timezone import validate_aware_utc

class SucursalCreate(BaseModel):
    nombre: constr(min_length=1, max_length=50) | None
    email: EmailStr = Field(max_length=255) | None
    rubro: constr(min_length=1, max_length=100) | None
    rubro2: constr(min_length=1, max_length=100) | None
    telefonos: list[Telefono]
    direccion: DireccionCreate # obligatorio al crear una Sucursal

    model_config = {"from_attributes": True}

class SucursalHomeOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    rubro: constr(min_length=1, max_length=100) | None
    rubro2: constr(min_length=1, max_length=100) | None
    calificacion: condecimal(ge=0, le=10, max_digits=4, decimal_places=2) | None
    telefonos: list[TelefonoConID]
    direccion: DireccionOut
    logo_url: constr(min_length=1, max_length=255) | None
    rol: Rol

    model_config = {"from_attributes": True}

class SucursalUpdateIn(BaseModel):
    '''
    Que en un campo se envíe None o no se envíe el campo directamente, significa que no se actualiza ese campo.
    No significa, por lo menos en este schema, que si algo no se envía,
    entonces se cambie en la base a NULL o se borre.
    '''
    nombre: constr(min_length=1, max_length=50) | None = None
    telefonos: list[TelefonoConID] | None = None  # [[id, numero], ...]. Si la lista viene vacía, se borran todos los teléfonos
    direccion: DireccionUpdateIn | None = None

    @root_validator(mode="before")
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        campos_permitidos_null = []

        for field, value in values.items():
            if field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema SucursalUpdateIn no puede enviarse como null')

        return values

class TurnoSucursalOut(BaseModel):
    id: conint(ge=1)
    usuario_dni: constr(regex=r"^[0-9]{6,8}$")
    usuario_apellido: constr(min_length=1, max_length=50)
    usuario_nombre: constr(min_length=1, max_length=50)
    usuario_email: EmailStr = Field(max_length=255)
    fecha_hora: datetime # debe salir como aware UTC
    servicio_id: conint(ge=1)
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

class TurnoHistorialSucursal(BaseModel):
    usuario_dni: constr(regex=r"^[0-9]{6,8}$")
    usuario_apellido: constr(min_length=1, max_length=50)
    usuario_nombre: constr(min_length=1, max_length=50)
    usuario_email: EmailStr = Field(max_length=255)
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

class HistorialSucursalOut(BaseModel):
    historial: list[TurnoHistorialSucursal]
    ultimo_cursor: datetime | None

    @field_validator("ultimo_cursor")
    def validar_fecha_hora_utc(value: datetime | None) -> datetime | None:
        return validate_aware_utc(value) if value else None

    model_config = {"from_attributes": True}

class ServicioSucursalOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion: constr(min_length=1, max_length=255) | None
    profesional_id: conint(ge=2) | None # 1 no se permite porque significa que no tiene profesional y debe salir como None
    profesional_dni: constr(regex=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    minutos_min_reserva: conint(ge=0)
    dias_max_reserva: conint(ge=0) | None
    cancelacion_limitada: bool
    disponibilidades: list[DisponibilidadServicio]

    model_config = {"from_attributes": True}

class ServicioCreate(BaseModel):
    nombre: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion: constr(min_length=1, max_length=255) | None
    profesional_id: conint(ge=2) | None # 1 no se permite porque significa que no tiene profesional y debe entrar como None
    minutos_min_reserva: conint(ge=0)
    dias_max_reserva: conint(ge=0) | None
    cancelacion_limitada: bool
    disponibilidades: list[DisponibilidadServicio] # Lista de disponibilidades por días

class ServicioUpdateIn(BaseModel):
    '''
    Que no se envíe el campo, significa que no se actualiza ese campo. No significa,
    por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL.

    En el caso de disponibilidades, pydantic no va a dejar que el usuario envíe None en su campo.
    Si el campo no se envía, entonces no se modifica, pero en caso de que sí se envíe y sea
    una lista vacía, entonces se interpreta como que quiere borrar todas las disponibilidades
    para con ese servicio y se procede a borrarlas a todas (que el programa identifique si envió disponibilidades
    o lo envió como lista vacía se hace en la función crud_sucursal.update_servicios en la parte que dice
    update_data = s.dict(exclude_unset=True)).
    Si hay alguna modificación en las disponibilidades, deberá enviarse todas las disponibilidades, no solo las que
    se modificaron.

    Todo campo que se envíe como None (y el validator lo permita), se cambia en la base a NULL.
    '''
    id: conint(ge=1) # obligatorio
    nombre: constr(min_length=1, max_length=100) | None = None
    duracion: conint(gt=0, multiple_of=5) | None = None
    precio: condecimal(ge=0, max_digits=10, decimal_places=2) | None = None
    aclaracion: constr(min_length=1, max_length=255) | None = None
    profesional_id: conint(ge=2) | None = None # 1 no se permite porque significa que no tiene profesional y debe entrar como None
    minutos_min_reserva: conint(ge=0) | None = None
    dias_max_reserva: conint(ge=0) | None = None
    cancelacion_limitada: bool | None = None
    disponibilidades: list[DisponibilidadServicio] | None = None # lista de disponibilidades por días
    
    @root_validator(mode="before")
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        campos_permitidos_null = ["aclaracion", "profesional_id", "dias_max_reserva"]

        for field, value in values.items():
            if field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema ServicioUpdateIn no puede enviarse como null')

        return values

    model_config = {"from_attributes": True}

class ServiciosDeleteIn(BaseModel):
    servicios: conlist(conint(ge=1), min_length=1) # IDs de servicios a eliminar

    model_config = {"from_attributes": True}

class UpdateRolIn(BaseModel):
    nuevo_rol: RolSucursal

    model_config = {"from_attributes": True}

class RolOut(BaseModel):
    rol: RolSucursal

    model_config = {"from_attributes": True}

class BlockUserIn(BaseModel):
    email: EmailStr = Field(max_length=255)
    motivo: constr(min_length=1, max_length=255) | None

    model_config = {"from_attributes": True}

class BlockUserOut(BaseModel):
    usuario_email: EmailStr = Field(max_length=255)
    miembro_dni: constr(regex=r"^[0-9]{6,8}$")
    miembro_apellido: constr(min_length=1, max_length=50)
    miembro_nombre: constr(min_length=1, max_length=50)
    miembro_rol: RolEmpresa | RolSucursal | None # rol dentro de la empresa o sucursal
    motivo: constr(min_length=1, max_length=255) | None
    created_at: datetime # debe salir como aware UTC

    @field_validator("created_at")
    def validar_fecha_hora_utc(value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = {"from_attributes": True}

class UnlockUserIn(BaseModel):
    email: EmailStr = Field(max_length=255)

    model_config = {"from_attributes": True}