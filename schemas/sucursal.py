from datetime import datetime, timedelta, date, time
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, conint, condecimal, constr, conlist, field_validator, model_validator

from schemas.common import (
    Telefono,
    TelefonoConID,
    DireccionCreate,
    DireccionOut,
    DireccionUpdateIn,
    ServicioOut,
    DisponibilidadServicio,
    ExcepcionFechaServicioOut,
    MiembroOut,
    NotificacionesOut,
    EstadoTurno,
    RolEmpresa,
    RolSucursal,
)
from core.timezone import validate_aware_utc

class SucursalCreate(BaseModel):
    empresa_id: conint(ge=1)
    nombre: constr(min_length=1, max_length=50)
    reserva_publica_habilitada: bool
    telefonos: list[Telefono]
    direccion: DireccionCreate # obligatorio al crear una sucursal

    model_config = ConfigDict(from_attributes=True)

class SucursalHomeOut(BaseModel): # Esto es solo para los gerentes de sucursal y empleados
    id: conint(ge=1)
    nombre_empresa: constr(min_length=1, max_length=50)
    nombre_sucursal: constr(min_length=1, max_length=50) | None
    logo_url: constr(min_length=1, max_length=255) | None
    notificaciones: NotificacionesOut
    rol: RolSucursal

    model_config = ConfigDict(from_attributes=True)

class SucursalPerfilOut(BaseModel): # Esto es solo para los gerentes de sucursal y empleados
    id: conint(ge=1)
    cuit: constr(pattern=r"^[0-9]{11}$")
    nombre_empresa: constr(min_length=1, max_length=50)
    nombre_sucursal: constr(min_length=1, max_length=50) | None
    email_empresa: EmailStr = Field(..., max_length=255)
    email_sucursal: EmailStr | None = Field(..., max_length=255)
    reserva_publica_habilitada: bool
    rubro: constr(min_length=1, max_length=100) | None
    rubro2: constr(min_length=1, max_length=100) | None
    calificacion: condecimal(ge=0, le=10, max_digits=4, decimal_places=2) | None
    telefonos: list[TelefonoConID]
    direccion: DireccionOut
    logo_url: constr(min_length=1, max_length=255) | None
    rol: RolSucursal

    model_config = ConfigDict(from_attributes=True)

class SucursalUpdateIn(BaseModel):
    nombre: constr(min_length=1, max_length=50) | None = None
    reserva_publica_habilitada: bool | None = None
    telefonos: list[TelefonoConID] | None = None # [[id, numero], ...]. Si la lista viene vacía, se borran todos los teléfonos
    direccion: DireccionUpdateIn | None = None

    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema SucursalUpdateIn")

        campos_permitidos_null = []

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema SucursalUpdateIn no puede enviarse como null')

        return values
    
    model_config = ConfigDict(from_attributes=True)

class ClienteOut(BaseModel):
    id: conint(ge=1)
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(..., max_length=255)
    telefono: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None
    telefono2: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None
    observacion: constr(min_length=1, max_length=500) | None
    fecha_hora_alta: datetime # debe salir como aware UTC
    activo: bool
    bloqueado: bool

    @field_validator("fecha_hora_alta", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class ClientesSucursalOut(BaseModel):
    clientes: list[ClienteOut]
    ultimo_cursor_id: conint(ge=1) | None

    model_config = ConfigDict(from_attributes=True)

class ClienteCreate(BaseModel):
    dni: constr(pattern=r"^[0-9]{6,8}$")
    apellido: constr(min_length=1, max_length=50)
    nombre: constr(min_length=1, max_length=50)
    email: EmailStr = Field(..., max_length=255)
    telefono: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None
    telefono2: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None
    observacion: constr(min_length=1, max_length=500) | None

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    model_config = ConfigDict(from_attributes=True)

class ClienteUpdateIn(BaseModel):
    dni: constr(pattern=r"^[0-9]{6,8}$") | None = None
    apellido: constr(min_length=1, max_length=50) | None = None
    nombre: constr(min_length=1, max_length=50) | None = None
    email: EmailStr | None = Field(default=None, max_length=255)
    telefono: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None = None
    telefono2: constr(pattern=r"^\+[1-9][0-9]{5,28}$") | None = None
    observacion: constr(min_length=1, max_length=500) | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema ClienteUpdateIn")

        campos_permitidos_null = ["telefono", "telefono2", "observacion"]

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema ClienteUpdateIn no puede enviarse como null')

        return values
    
    model_config = ConfigDict(from_attributes=True)

class TurnoSucursalOut(BaseModel):
    id: conint(ge=1)
    cliente_dni: constr(pattern=r"^[0-9]{6,8}$")
    cliente_apellido: constr(min_length=1, max_length=50)
    cliente_nombre: constr(min_length=1, max_length=50)
    cliente_email: EmailStr = Field(..., max_length=255)
    fecha_hora: datetime # debe salir como aware UTC
    servicio_id: conint(ge=1)
    nombre_de_servicio: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(pattern=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    created_at: datetime
    estado_turno: EstadoTurno

    @field_validator("fecha_hora", "created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class ReservaTurnoSucursalIn(BaseModel):
    cliente_id: conint(ge=1)
    servicio_id: conint(ge=1)
    fecha_hora: datetime # debe llegar como aware UTC

    @field_validator("fecha_hora", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class TurnoEstadoUpdateIn(BaseModel):
    estado_turno: EstadoTurno
    observacion: constr(min_length=1, max_length=255) | None # por ejemplo: el motivo de cancelación

    model_config = ConfigDict(from_attributes=True)

class TurnoHistorialSucursal(BaseModel):
    cliente_dni: constr(pattern=r"^[0-9]{6,8}$")
    cliente_apellido: constr(min_length=1, max_length=50)
    cliente_nombre: constr(min_length=1, max_length=50)
    cliente_email: EmailStr = Field(..., max_length=255)
    fecha_hora: datetime # debe salir como aware UTC
    nombre_de_servicio: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion_de_servicio: constr(min_length=1, max_length=255) | None
    profesional_dni: constr(pattern=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    created_at: datetime
    estado_turno: EstadoTurno

    @field_validator("fecha_hora", "created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)

class HistorialSucursalOut(BaseModel):
    historial: list[TurnoHistorialSucursal]
    ultimo_cursor_fecha_hora: datetime | None
    ultimo_cursor_id: conint(ge=1) | None

    @field_validator("ultimo_cursor_fecha_hora", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime | None) -> datetime | None:
        return validate_aware_utc(value) if value else None

    model_config = ConfigDict(from_attributes=True)

class ServicioSucursalOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=100)
    aclaracion: constr(min_length=1, max_length=255) | None
    profesional_id: conint(ge=1) | None
    profesional_dni: constr(pattern=r"^[0-9]{6,8}$") | None
    profesional_apellido: constr(min_length=1, max_length=50) | None
    profesional_nombre: constr(min_length=1, max_length=50) | None
    minutos_min_reserva: conint(ge=0)
    dias_max_reserva: conint(ge=0) | None
    cancelacion_limitada: bool
    servicios: conlist(ServicioOut, min_length=1)
    excepciones_fechas: list[ExcepcionFechaServicioOut]

    model_config = ConfigDict(from_attributes=True)

class ServicioBaseCreate(BaseModel):
    nombre: constr(min_length=1, max_length=100)
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    aclaracion: constr(min_length=1, max_length=255) | None
    profesional_id: conint(ge=1) | None
    vigente_desde: date
    vigente_hasta: date | None
    minutos_min_reserva: conint(ge=0)
    dias_max_reserva: conint(ge=0) | None
    cancelacion_limitada: bool
    disponibilidades: list[DisponibilidadServicio] # Lista de disponibilidades por días

    @field_validator("vigente_desde", mode="after")
    @classmethod
    def validar_vigente_desde_mayor_a_hoy(cls, value: date) -> date:

        fecha_hoy_local = timezone.utc_to_local(timezone.now_utc()).date()
        fecha_tomorrow_local = fecha_hoy_local + timedelta(days=1)

        if value < fecha_tomorrow_local:
            raise ValueError("La fecha vigente_desde debe ser como mínimo la de mañana")

        return value

    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.vigente_desde
        fin = self.vigente_hasta

        if inicio is not None and fin is not None:
            if fin < inicio:
                raise ValueError("La fecha final de la vigencia del servicio debe ser mayor o igual que la fecha de inicio")

        return self

    model_config = ConfigDict(from_attributes=True)

class ServicioBaseUpdateIn(BaseModel):
    '''
    Que no se envíe el campo, significa que no se actualiza ese campo. No significa,
    por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL.

    Todo campo que se envíe como None (y el validator lo permita), se cambia en la base a NULL.
    '''
    nombre: constr(min_length=1, max_length=100) | None = None
    aclaracion: constr(min_length=1, max_length=255) | None = None
    minutos_min_reserva: conint(ge=0) | None = None
    dias_max_reserva: conint(ge=0) | None = None
    cancelacion_limitada: bool | None = None
    
    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema ServicioBaseUpdateIn")

        campos_permitidos_null = ["aclaracion", "dias_max_reserva"]

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema ServicioBaseUpdateIn no puede enviarse como null')

        return values

    model_config = ConfigDict(from_attributes=True)

class ServiciosBaseDeleteIn(BaseModel):
    servicios_base: conlist(conint(ge=1), min_length=1) # IDs de servicios base a eliminar

    model_config = ConfigDict(from_attributes=True)

class ServicioCreate(BaseModel):
    duracion: conint(gt=0, multiple_of=5)
    precio: condecimal(ge=0, max_digits=10, decimal_places=2)
    vigente_desde: date
    vigente_hasta: date | None
    disponibilidades: list[DisponibilidadServicio]

    @field_validator("vigente_desde", mode="after")
    @classmethod
    def validar_vigente_desde_mayor_a_hoy(cls, value: date) -> date:

        fecha_hoy_local = timezone.utc_to_local(timezone.now_utc()).date()
        fecha_tomorrow_local = fecha_hoy_local + timedelta(days=1)

        if value < fecha_tomorrow_local:
            raise ValueError("La fecha vigente_desde debe ser como mínimo la de mañana")

        return value

    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.vigente_desde
        fin = self.vigente_hasta

        if inicio is not None and fin is not None:
            if fin < inicio:
                raise ValueError("La fecha final de la vigencia del servicio debe ser mayor o igual que la fecha de inicio")

        return self

    model_config = ConfigDict(from_attributes=True)

class ServicioUpdateIn(BaseModel):
    '''
    Que no se envíe el campo, significa que no se actualiza ese campo. No significa,
    por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL.

    En el caso de disponibilidades, pydantic no va a dejar que el usuario envíe None en su campo.
    Si el campo disponibilidades no se envía, entonces no se modifica, pero en caso de que sí se envíe y sea
    una lista vacía, entonces se interpreta como que quiere borrar todas las disponibilidades
    para con ese servicio y se procede a borrarlas a todas (que el programa identifique si envió disponibilidades
    o lo envió como lista vacía se hace en la función crud_sucursal.update_servicio_version en la parte que dice
    update_data = servicio_update.model_dump(exclude_unset=True)).
    Si hay alguna modificación en las disponibilidades, deberá enviarse todas las disponibilidades, no solo las que
    se modificaron.

    Todo campo que se envíe como None (y el validator lo permita), se cambia en la base a NULL.
    '''
    precio: condecimal(ge=0, max_digits=10, decimal_places=2) | None = None
    vigente_hasta: date | None = None
    disponibilidades: list[DisponibilidadServicio] | None = None # lista de disponibilidades por días
    
    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema ServicioUpdateIn")

        campos_permitidos_null = ["vigente_hasta"]

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema ServicioUpdateIn no puede enviarse como null')

        return values

    model_config = ConfigDict(from_attributes=True)

class ExcepcionFechaServicioCreate(BaseModel):
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

class ExcepcionFechaServicioUpdateIn(BaseModel):
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    motivo: constr(min_length=1, max_length=255) | None = None

    @model_validator(mode="before")
    @classmethod
    def validar_campos_not_null(cls, values):
        """
        Rechaza cualquier campo que sea explícitamente enviado como None, exceptuando los campos en la lista de campos permitidos.
        Los campos que no se envíen simplemente se ignoran.
        """
        if not isinstance(values, dict):
            # si bien significa que el front envió cualquier cosa, lo devolvemos tal cual para que pydantic se encargue de tirar error
            return values
        
        if not values:
            raise ValueError("Debe enviarse al menos un campo en el schema ExcepcionFechaServicioUpdateIn")

        campos_permitidos_null = ["motivo"]

        for field, value in values.items():
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema ExcepcionFechaServicioUpdateIn no puede enviarse como null')

        return values
    
    @model_validator(mode="after")
    def validar_consistencia(self) -> Self:
        inicio = self.fecha_inicio
        fin = self.fecha_fin

        if inicio is not None and fin is not None:
            if fin < inicio:
                raise ValueError("La fecha final de una excepción de servicio debe ser mayor o igual que la fecha de inicio")

        return self
    
    model_config = ConfigDict(from_attributes=True)

class MiembroSucursalOut(BaseModel):
    miembro: MiembroOut
    rol: RolSucursal

    model_config = ConfigDict(from_attributes=True)

class MiembroSucursalAddIn(BaseModel):
    rol: RolSucursal

    model_config = ConfigDict(from_attributes=True)

class BlockClienteIn(BaseModel):
    motivo: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class BlockClienteOut(BaseModel):
    cliente: ClienteOut
    miembro_dni: constr(pattern=r"^[0-9]{6,8}$")
    miembro_apellido: constr(min_length=1, max_length=50)
    miembro_nombre: constr(min_length=1, max_length=50)
    miembro_rol: RolEmpresa | RolSucursal | None # rol dentro de la empresa o sucursal
    motivo: constr(min_length=1, max_length=255) | None
    created_at: datetime # debe salir como aware UTC

    @field_validator("created_at", mode="after")
    @classmethod
    def validar_fecha_hora_utc(cls, value: datetime) -> datetime:
        return validate_aware_utc(value)

    model_config = ConfigDict(from_attributes=True)