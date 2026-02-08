from datetime import datetime, date, time
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, conint, constr, field_validator, model_validator, root_validator

from schemas.common import Telefono

class UserLogin(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: constr(min_length=8, max_length=128, strip_whitespace=True)
    
    model_config = {"from_attributes": True}

class ChangePassword(BaseModel):
    old_password: constr(min_length=8, max_length=128, strip_whitespace=True)
    new_password: constr(min_length=8, max_length=128, strip_whitespace=True)

    model_config = {"from_attributes": True}

class ForgotPasswordEmail(BaseModel):
    email: EmailStr = Field(max_length=255)

    model_config = {"from_attributes": True}

class ResetPasswordEmail(BaseModel):
    token: constr(min_length=20, max_length=1000)
    new_password: constr(min_length=8, max_length=128, strip_whitespace=True)

    model_config = {"from_attributes": True}

class FormaEnvio(str, Enum):
    sms = "sms"
    wpp = "wpp"

class ForgotPasswordMobile(BaseModel):
    email: EmailStr = Field(max_length=255)
    telefono: Telefono
    forma: FormaEnvio # sms o wpp

    model_config = {"from_attributes": True}

class ResetPasswordMobile(BaseModel):
    telefono: Telefono
    otp: constr(regex=r"^\d{6}$") # numérico de 6 dígitos
    new_password: constr(min_length=8, max_length=128, strip_whitespace=True)

    model_config = {"from_attributes": True}