from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, conint, condecimal, constr, conlist, field_validator, model_validator

from schemas.common import (
    Telefono,
    TelefonoConID,
    DireccionCreate,
    DireccionOut,
    MiembroOut,
    NotificacionesOut,
    RolEmpresa,
    RolSucursal,
)

class EmpresaCreate(BaseModel):
    cuit: constr(pattern=r"^[0-9]{11}$")
    nombre: constr(min_length=1, max_length=40)
    email: EmailStr = Field(..., max_length=255)
    rubro: constr(min_length=1, max_length=50) | None
    rubro2: constr(min_length=1, max_length=50) | None
    reserva_publica_habilitada: bool
    telefonos: list[Telefono] # se va a guardar en la sucursal que se hace por defecto
    direccion: DireccionCreate # obligatorio al crear una empresa (se va a guardar en la sucursal que se hace por defecto)

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    model_config = ConfigDict(from_attributes=True)

class SucursalPerfilOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=40) | None # sin incluir el nombre original de la empresa; si la empresa tiene una sola sucursal, nombre es None sí o sí
    email: EmailStr | None = Field(..., max_length=255)
    reserva_publica_habilitada: bool
    calificacion: condecimal(ge=0, le=10, max_digits=4, decimal_places=2) | None
    activa: bool
    telefonos: list[TelefonoConID]
    direccion: DireccionOut

    model_config = ConfigDict(from_attributes=True)

class EmpresaHomeOut(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=40)
    logo_url: constr(min_length=1, max_length=255) | None
    sucursales: list[SucursalPerfilOut]
    notificaciones: NotificacionesOut
    rol: RolEmpresa

    model_config = ConfigDict(from_attributes=True)

class EmpresaPerfilOut(BaseModel):
    id: conint(ge=1)
    cuit: constr(pattern=r"^[0-9]{11}$")
    nombre: constr(min_length=1, max_length=40)
    email: EmailStr = Field(..., max_length=255)
    rubro: constr(min_length=1, max_length=50) | None
    rubro2: constr(min_length=1, max_length=50) | None
    logo_url: constr(min_length=1, max_length=255) | None
    sucursales: list[SucursalPerfilOut]

    model_config = ConfigDict(from_attributes=True)

class EmpresaUpdateIn(BaseModel):
    cuit: constr(pattern=r"^[0-9]{11}$") | None = None
    nombre: constr(min_length=1, max_length=40) | None = None
    rubro: constr(min_length=1, max_length=50) | None = None
    rubro2: constr(min_length=1, max_length=50) | None = None

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
            raise ValueError("Debe enviarse al menos un campo en el schema EmpresaUpdateIn")

        campos_permitidos_null = ["rubro", "rubro2"]

        for field, value in values.items():
            # field in cls.model_fields asegura que si el front envía datos basura de más, el validator los deje pasar y no tire error
            if field in cls.model_fields and field not in campos_permitidos_null and value is None:
                raise ValueError(f'El campo "{field}" en el schema EmpresaUpdateIn no puede enviarse como null')

        return values
    
    model_config = ConfigDict(from_attributes=True)

class EmpresaLogoOut(BaseModel):
    logo_url: constr(min_length=1, max_length=255) | None

    model_config = ConfigDict(from_attributes=True)

class MiembroEmpresaOut(BaseModel):
    miembro: MiembroOut
    rol: RolEmpresa # rol dentro de la empresa

    model_config = ConfigDict(from_attributes=True)

class SucursalDeMiembro(BaseModel):
    id: conint(ge=1)
    nombre: constr(min_length=1, max_length=40) | None # sin incluir el nombre original de la empresa; si la empresa tiene una sola sucursal, nombre es None sí o sí
    rol: RolSucursal # rol dentro de la sucursal

    model_config = ConfigDict(from_attributes=True)

class MiembroSucursalOut(BaseModel):
    miembro: MiembroOut
    sucursales: conlist(SucursalDeMiembro, min_length=1)

    model_config = ConfigDict(from_attributes=True)

class MiembrosEmpresaOut(BaseModel):
    miembros_empresa: list[MiembroEmpresaOut]
    miembros_sucursales: list[MiembroSucursalOut]

    model_config = ConfigDict(from_attributes=True)