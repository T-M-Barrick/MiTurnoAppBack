from datetime import datetime, date, time

from pydantic import BaseModel, EmailStr, constr

from schemas.common import RolEmpresa, RolSucursal

class InvitacionEmpleadoIn(BaseModel):
    usuario_email: EmailStr = Field(max_length=255)
    rol: RolEmpresa | RolSucursal

    model_config = {"from_attributes": True}

class InvitacionEmpresaAceptadaOut(BaseModel):
    empresa: constr(min_length=1, max_length=50)
    rol: RolEmpresa

    model_config = {"from_attributes": True}

class InvitacionSucursalAceptadaOut(BaseModel):
    sucursal: constr(min_length=1, max_length=50)
    rol: RolSucursal

    model_config = {"from_attributes": True}

class TokenRequest(BaseModel):
    token: constr(min_length=20, max_length=1000)

    model_config = {"from_attributes": True}