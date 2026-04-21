from datetime import datetime
from enum import Enum
from typing import Self, Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, conint, confloat, constr, field_validator, model_validator

from core.timezone import validate_aware_utc

class EstadoTurno(str, Enum):
    CONFIRMADO = "CONFIRMADO"
    CANCELADO_POR_USUARIO = "CANCELADO_POR_USUARIO"
    CANCELADO_POR_EMPRESA = "CANCELADO_POR_EMPRESA"
    CUMPLIDO = "CUMPLIDO"
    NO_CUMPLIDO = "NO_CUMPLIDO"

class RolEmpresa(str, Enum):
    PROPIETARIO = "PROPIETARIO"
    GERENTE_EMPRESA = "GERENTE_EMPRESA"

class RolSucursal(str, Enum):
    GERENTE_SUCURSAL = "GERENTE_SUCURSAL"
    EMPLEADO = "EMPLEADO"

class Telefono(BaseModel):
    # El texto debe contener solo números del 0 al 9 luego de que el primer caracter sea el + y el siguiente sea un dígito entre 1 y 9
    numero: constr(pattern=r"^\+[1-9][0-9]{5,28}$")

    model_config = ConfigDict(from_attributes=True)

class TelefonoConID(BaseModel):
    id: conint(ge=0) # 0 por si se crea un teléfono nuevo en los updates de usuarios o sucursales
    # El texto debe contener solo números del 0 al 9 luego de que el primer caracter sea el + y el siguiente sea un dígito entre 1 y 9
    numero: constr(pattern=r"^\+[1-9][0-9]{5,28}$")

    model_config = ConfigDict(from_attributes=True)

class DireccionCreate(BaseModel):
    calle: constr(min_length=1, max_length=255)
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255)
    departamento: constr(min_length=1, max_length=255)
    provincia: constr(min_length=1, max_length=255)
    pais: constr(min_length=1, max_length=255)
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    @field_validator("lat", "lng", mode="after")
    @classmethod
    def normalizar_coordenada(cls, value: float) -> float:
        return round(value, 6)

    model_config = ConfigDict(from_attributes=True)

class DireccionOut(BaseModel):
    id: conint(ge=1)
    calle: constr(min_length=1, max_length=255)
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255)
    departamento: constr(min_length=1, max_length=255)
    provincia: constr(min_length=1, max_length=255)
    pais: constr(min_length=1, max_length=255)
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    @field_validator("lat", "lng", mode="after")
    @classmethod
    def normalizar_coordenada(cls, value: float) -> float:
        return round(value, 6)

    model_config = ConfigDict(from_attributes=True)

class DireccionUpdateIn(BaseModel):
    '''
    Todos los campos son obligatorios de enviar en este schema.
    Que en un campo se envíe None significa que se actualiza ese atributo en la base como NULL
    '''
    id: conint(ge=0) # 0 por si se crea una dirección nueva en el update de usuarios
    calle: constr(min_length=1, max_length=255)
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255)
    departamento: constr(min_length=1, max_length=255)
    provincia: constr(min_length=1, max_length=255)
    pais: constr(min_length=1, max_length=255)
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    @field_validator("lat", "lng", mode="after")
    @classmethod
    def normalizar_coordenada(cls, value: float) -> float:
        return round(value, 6)

    model_config = ConfigDict(from_attributes=True)

class TurnoEstadoOut(BaseModel):
    id: conint(ge=1)
    estado: EstadoTurno

    model_config = ConfigDict(from_attributes=True)

class MiembroOut(BaseModel):
    id: conint(ge=1)
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=30)
    nombre: constr(min_length=1, max_length=30)
    email: EmailStr = Field(..., max_length=255)

    model_config = ConfigDict(from_attributes=True)

class UpdateRolIn(BaseModel):
    nuevo_rol: RolEmpresa | RolSucursal
    sucursal_id: conint(ge=1) | None

    @model_validator(mode="after")
    def validar_nuevo_rol(self) -> Self:
        if isinstance(self.nuevo_rol, RolSucursal) and self.sucursal_id is None:
            raise ValueError("Debe especificarse la sucursal del nuevo miembro")
        return self

    model_config = ConfigDict(from_attributes=True)

class NotificacionOut(BaseModel):
    id: conint(ge=1)
    tipo: constr(min_length=1, max_length=50)
    extra_data: dict[str, Any] | None
    created_at: datetime
    leida: bool

    @field_validator("created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class NotificacionesOut(BaseModel):
    notificaciones: list[NotificacionOut]
    ultimo_cursor_id: conint(ge=1) | None

    model_config = ConfigDict(from_attributes=True)