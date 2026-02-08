from datetime import datetime, date, time
from enum import Enum

from pydantic import BaseModel, Field, conint, confloat, constr, field_validator, model_validator, root_validator

class EstadoTurno(str, Enum):
    CONFIRMADO = "CONFIRMADO"
    CANCELADO_POR_USUARIO = "CANCELADO_POR_USUARIO"
    CANCELADO_POR_EMPRESA = "CANCELADO_POR_EMPRESA"
    CUMPLIDO = "CUMPLIDO"
    NO_CUMPLIDO = "NO_CUMPLIDO"

class RolEmpresa(str, Enum):
    propietario = "propietario"
    gerente_general = "gerente_general"

class RolSucursal(str, Enum):
    gerente = "gerente"
    empleado = "empleado"

class Telefono(BaseModel):
    # El texto debe contener solo números del 0 al 9 luego de que el primer caracter sea el + y el siguiente sea un dígito entre 1 y 9
    numero: constr(regex=r"^\+[1-9][0-9]{5,28}$")

    model_config = {"from_attributes": True}

class TelefonoConID(BaseModel):
    id: conint(ge=1)
    # El texto debe contener solo números del 0 al 9 luego de que el primer caracter sea el + y el siguiente sea un dígito entre 1 y 9
    numero: constr(regex=r"^\+[1-9][0-9]{5,28}$")

    model_config = {"from_attributes": True}

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

    model_config = {"from_attributes": True}

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

    model_config = {"from_attributes": True}

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

    model_config = {"from_attributes": True}

class TurnoUpdateIn(BaseModel):
    id: conint(ge=1)
    estado_turno: EstadoTurno | None = None
    motivo: constr(min_length=1, max_length=255) | None = None
    recordatorio: conint(ge=0, le=1410, multiple_of=30) | None = None # minutos antes

    @root_validator(mode="before")
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        campos_permitidos_null = ["motivo", "recordatorio"]

        for field, value in values.items():
            if field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema TurnoUpdateIn no puede enviarse como null')

        return values

    model_config = {"from_attributes": True}

class TurnoEstadoOut(BaseModel):
    id: conint(ge=1)
    estado: EstadoTurno

    model_config = {"from_attributes": True}

class DisponibilidadServicio(BaseModel):
    dia: conint(ge=0, le=6) # 0 = lunes, 6 = domingo
    hora_inicio: time
    hora_fin: time
    intervalo: conint(gt=0, multiple_of=5)
    cant_turnos_max: conint(ge=0)

    @field_validator("hora_inicio", "hora_fin")
    def validar_hora_5min(value):
        if value.minute % 5 != 0:
            raise ValueError("HORA_MULTIPLO_5")
        return value
    
    @model_validator(mode="after")
    def validar_consistencia(cls, values):
        inicio = values.hora_inicio
        fin = values.hora_fin
        intervalo = values.intervalo

        if fin < inicio:
            raise ValueError("INVALID_TIME_RANGE")

        # convertir a minutos
        inicio_min = inicio.hour * 60 + inicio.minute
        fin_min = fin.hour * 60 + fin.minute
        duracion_total = fin_min - inicio_min

        if duracion_total % intervalo != 0:
            raise ValueError("INVALID_TIME_RANGE_WITH_INTERVALO")

        return values
    
    model_config = {"from_attributes": True}

class MiembroOut(BaseModel):
    id: conint(ge=1)
    dni: constr(regex=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=255)
    rol: RolEmpresa | RolSucursal

    model_config = {"from_attributes": True}