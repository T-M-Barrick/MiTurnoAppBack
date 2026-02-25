from datetime import datetime, timedelta, date, time
from typing import Self

from pydantic import BaseModel, Field, conint, confloat, constr, field_validator, model_validator

from schemas.common import RolEmpresa, RolSucursal

class InvitacionEmpleadoIn(BaseModel):
    usuario_email: EmailStr = Field(..., max_length=255)
    rol: RolEmpresa | RolSucursal
    empresa_id: conint(ge=1)
    sucursal_id: conint(ge=1) | None = None

    @model_validator(mode="after")
    def validar_rol_vs_scope(self) -> Self:
        if self.sucursal_id:
            if not isinstance(self.rol, RolSucursal):
                raise ValueError(
                    "Si se envía sucursal_id, el rol debe ser de sucursal"
                )
        else:
            if not isinstance(self.rol, RolEmpresa):
                raise ValueError(
                    "Si no se envía sucursal_id, el rol debe ser de empresa"
                )
        return self

    model_config = {"from_attributes": True}

class InvitacionAceptadaOut(BaseModel):
    nombre: constr(min_length=1, max_length=100) # puede ser nombre de empresa o nombre completo de sucursal (empresa - sucursal)
    rol: RolEmpresa | RolSucursal

    model_config = {"from_attributes": True}