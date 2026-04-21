from datetime import datetime
from typing import Self, Any

from pydantic import (
    BaseModel, ConfigDict, EmailStr, SecretStr, Field, conint, condecimal, constr, conlist, field_validator, model_validator
)

from schemas.common import (
    Telefono,
    TelefonoConID,
    DireccionCreate,
    DireccionOut,
    DireccionUpdateIn,
    NotificacionesOut,
    EstadoTurno,
    RolEmpresa,
    RolSucursal,
)
from core.timezone import validate_aware_utc
from core.security import validate_password

class UserCreate(BaseModel):
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=30)
    nombre: constr(min_length=1, max_length=30)
    email: EmailStr = Field(..., max_length=255)
    password: SecretStr = Field(..., min_length=8, max_length=128)
    recordatorio_minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None
    telefonos: conlist(Telefono, min_length=1)
    direcciones: conlist(DireccionCreate, min_length=1)

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    @field_validator("password", mode="after")
    @classmethod
    def validar_password(cls, value: SecretStr) -> SecretStr:

        validate_password(value.get_secret_value())
        return value

    model_config = ConfigDict(from_attributes=True)

class SucursalOut(BaseModel):
    id: conint(ge=1)
    cuit: constr(pattern=r"^[0-9]{11}$")
    nombre: constr(min_length=1, max_length=83) # nombre completo (empresa - sucursal)
    email: EmailStr = Field(..., max_length=255)
    rubro: constr(min_length=1, max_length=50) | None
    rubro2: constr(min_length=1, max_length=50) | None
    calificacion: condecimal(ge=0, le=10, max_digits=4, decimal_places=2) | None
    telefonos: list[Telefono]
    direccion: DireccionOut
    logo_url: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class TurnoUserOut(BaseModel):
    id: conint(ge=1)
    sucursal_id: conint(ge=1)
    sucursal: constr(min_length=1, max_length=83) # nombre completo (empresa - sucursal)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    direccion: DireccionOut
    fecha_hora: datetime # debe salir como aware UTC
    nombre_de_servicio: constr(min_length=1, max_length=50)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(pattern=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=30) | None
    profesional_nombre: constr(min_length=1, max_length=30) | None
    created_at: datetime
    estado_turno: EstadoTurno
    recordatorio_minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None

    @field_validator("fecha_hora", "created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class UserLoginOut(BaseModel):
    id: conint(ge=1)
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=30)
    nombre: constr(min_length=1, max_length=30)
    email: EmailStr = Field(..., max_length=255)
    recordatorio_minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None
    telefonos: conlist(TelefonoConID, min_length=1)
    direcciones: conlist(DireccionOut, min_length=1)
    favoritos: list[SucursalOut]
    turnos: list[TurnoUserOut]
    notificaciones: NotificacionesOut

    model_config = ConfigDict(from_attributes=True)

class UserUpdateIn(BaseModel):
    dni: constr(pattern=r"^[0-9]{6,8}$") | None = None
    apellido: constr(min_length=1, max_length=30) | None = None
    nombre: constr(min_length=1, max_length=30) | None = None
    recordatorio_minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None = None
    telefonos: conlist(TelefonoConID, min_length=1) | None = None 
    direcciones: conlist(DireccionUpdateIn, min_length=1) | None = None

    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values: Any) -> Any:
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema UserUpdateIn")

        campos_permitidos_null = ["recordatorio_minutos_antes"]

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema UserUpdateIn no puede enviarse como null')

        return values

    model_config = ConfigDict(from_attributes=True)

class UserUpdateOut(BaseModel):
    id: conint(ge=1)
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=30)
    nombre: constr(min_length=1, max_length=30)
    email: EmailStr = Field(..., max_length=255)
    recordatorio_minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None
    telefonos: conlist(TelefonoConID, min_length=1)
    direcciones: conlist(DireccionOut, min_length=1)

    model_config = ConfigDict(from_attributes=True)

class RolEmpresaOut(BaseModel):
    empresa_id: conint(ge=1)
    nombre_empresa: constr(min_length=1, max_length=40)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    email: EmailStr = Field(..., max_length=255)
    rol: RolEmpresa
    
    model_config = ConfigDict(from_attributes=True)

class RolSucursalOut(BaseModel):
    sucursal_id: conint(ge=1)
    nombre_sucursal: constr(min_length=1, max_length=83) # nombre completo (empresa - sucursal)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    email: EmailStr = Field(..., max_length=255)
    rol: RolSucursal
    
    model_config = ConfigDict(from_attributes=True)

class MisEmpresasOut(BaseModel): # para cuando un usuario pide las empresas en las que trabaja
    empresas: list[RolEmpresaOut]
    sucursales: list[RolSucursalOut]

    model_config = ConfigDict(from_attributes=True)

class ReservaTurnoUserIn(BaseModel):
    sucursal_id: conint(ge=1)
    servicio_id: conint(ge=1)
    fecha_hora: datetime # debe llegar como aware UTC

    @field_validator("fecha_hora", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

# Esto es para que el usuario pueda mandar que no le importa el profesional del servicio que está reservando.
# El chequeo de que sea el mismo servicio o no se hace en la función crud.
class ReservaTurnoOpcionesUserIn(BaseModel):
    opciones: conlist(ReservaTurnoUserIn, min_length=1)

    @model_validator(mode="after")
    def validar_sucursal_id_y_fecha_hora(self) -> Self:
        opciones = self.opciones

        # Tomo el primer elemento como referencia
        sucursal_id_ref = opciones[0].sucursal_id
        fecha_hora_ref = opciones[0].fecha_hora

        for opt in opciones[1:]: # empezamos desde el segundo para ahorrar un ciclo
            if opt.sucursal_id != sucursal_id_ref:
                raise ValueError("Todas las reservas deben tener el mismo sucursal_id")
            if opt.fecha_hora != fecha_hora_ref:
                raise ValueError("Todas las reservas deben tener la misma fecha_hora")

        return self

    model_config = ConfigDict(from_attributes=True)

class TurnoEstadoUpdateIn(BaseModel):
    estado_turno: EstadoTurno
    motivo: constr(min_length=1, max_length=255) | None # por ejemplo: el motivo de cancelación
    calificacion: conint(ge=0, le=10) | None # solo permite enteros de 0 a 10

    @model_validator(mode="after")
    def validar_calificacion(self) -> Self:

        if self.calificacion is not None and self.estado_turno != EstadoTurno.CUMPLIDO:
            raise ValueError("Solo se puede calificar un turno cumplido")

        return self

    model_config = ConfigDict(from_attributes=True)

class TurnoRecordatorioUpdateIn(BaseModel):
    minutos_antes: conint(ge=30, le=1410, multiple_of=30) | None

    model_config = ConfigDict(from_attributes=True)

class TurnoHistorialUser(BaseModel):
    id: conint(ge=1)
    sucursal: constr(min_length=1, max_length=83) # nombre completo (empresa - sucursal)
    logo_empresa_url: constr(min_length=1, max_length=255) | None
    fecha_hora: datetime # debe salir como aware UTC
    nombre_de_servicio: constr(min_length=1, max_length=50)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(pattern=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=30) | None
    profesional_nombre: constr(min_length=1, max_length=30) | None
    created_at: datetime
    estado_turno: EstadoTurno

    @field_validator("fecha_hora", "created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class HistorialUserOut(BaseModel):
    historial: list[TurnoHistorialUser]
    ultimo_cursor_fecha_hora: datetime | None
    ultimo_cursor_id: conint(ge=1) | None

    @field_validator("ultimo_cursor_fecha_hora", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime | None) -> datetime | None:
        return validate_aware_utc(value) if value else None

    model_config = ConfigDict(from_attributes=True)

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