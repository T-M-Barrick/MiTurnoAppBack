from datetime import datetime, timedelta, date, time
from enum import Enum
from typing import Self, Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, conint, condecimal, confloat, constr, field_validator, model_validator

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
    id: conint(ge=1)
    # El texto debe contener solo números del 0 al 9 luego de que el primer caracter sea el + y el siguiente sea un dígito entre 1 y 9
    numero: constr(pattern=r"^\+[1-9][0-9]{5,28}$")

    model_config = ConfigDict(from_attributes=True)

class DireccionCreate(BaseModel):
    calle: constr(min_length=1, max_length=255) | None
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255) | None
    departamento: constr(min_length=1, max_length=255) | None
    provincia: constr(min_length=1, max_length=255) | None
    pais: constr(min_length=1, max_length=255) | None
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class DireccionOut(BaseModel):
    id: conint(ge=1)
    calle: constr(min_length=1, max_length=255) | None
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255) | None
    departamento: constr(min_length=1, max_length=255) | None
    provincia: constr(min_length=1, max_length=255) | None
    pais: constr(min_length=1, max_length=255) | None
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class DireccionUpdateIn(BaseModel):
    '''
    Todos los campos son obligatorios de enviar en este schema.
    Que en un campo se envíe None significa que se actualiza ese atributo en la base como NULL
    '''
    id: conint(ge=1)
    calle: constr(min_length=1, max_length=255) | None
    altura: constr(min_length=1, max_length=255) | None
    localidad: constr(min_length=1, max_length=255) | None
    departamento: constr(min_length=1, max_length=255) | None
    provincia: constr(min_length=1, max_length=255) | None
    pais: constr(min_length=1, max_length=255) | None
    lat: confloat(ge=-90, le=90)
    lng: confloat(ge=-180, le=180)
    aclaracion: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class TurnoEstadoOut(BaseModel):
    id: conint(ge=1)
    estado: EstadoTurno

    model_config = ConfigDict(from_attributes=True)

class DisponibilidadServicio(BaseModel):
    dia: conint(ge=0, le=6) # 0 = lunes, 6 = domingo
    hora_inicio: time
    hora_fin: time
    intervalo: conint(gt=0, multiple_of=5)
    cant_turnos_max: conint(ge=0)

    @field_validator("hora_inicio", "hora_fin", mode="after")
    @classmethod
    def validar_hora_5min(cls, value: time) -> time:
        if value.minute % 5 != 0:
            raise ValueError("La hora debe ser múltiplo de 5 minutos")
        return value
    
    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.hora_inicio
        fin = self.hora_fin
        intervalo = self.intervalo

        if fin < inicio:
            raise ValueError("La hora final debe ser mayor o igual que la hora de inicio")

        # convertir a minutos
        inicio_min = inicio.hour * 60 + inicio.minute
        fin_min = fin.hour * 60 + fin.minute
        duracion_total = fin_min - inicio_min

        if duracion_total % intervalo != 0:
            raise ValueError("La hora final debe coincidir exactamente con múltiplos del intervalo desde la hora de inicio")

        return self
    
    model_config = ConfigDict(from_attributes=True)

class ServicioOut(BaseModel):
    id: conint(ge=1)
    servicio_base_id: conint(ge=1)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    vigente_desde: date
    vigente_hasta: date | None
    created_at: datetime
    modify_at: datetime | None
    disponibilidades: list[DisponibilidadServicio]

    @field_validator("created_at", "modify_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime | None) -> datetime | None:
        return validate_aware_utc(value) if value else None

    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.vigente_desde
        fin = self.vigente_hasta

        if inicio is not None and fin is not None:
            if fin < inicio:
                raise ValueError("La fecha final de la vigencia del servicio debe ser mayor o igual que la fecha de inicio")

        return self

    model_config = ConfigDict(from_attributes=True)

class ExcepcionFechaServicioOut(BaseModel):
    id: conint(ge=1)
    fecha_inicio: date
    fecha_fin: date
    motivo: constr(min_length=1, max_length=255) | None
    
    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.fecha_inicio
        fin = self.fecha_fin

        if fin < inicio:
            raise ValueError("La fecha final de una excepción de servicio debe ser mayor o igual que la fecha de inicio")

        return self
    
    model_config = ConfigDict(from_attributes=True)

class MiembroOut(BaseModel):
    id: conint(ge=1)
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
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