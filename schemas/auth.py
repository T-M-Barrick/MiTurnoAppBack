from datetime import datetime, timedelta, date, time
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, Field, conint, constr, field_validator, model_validator

from schemas.common import Telefono
from core.security import validate_password

'''
Cuando Pydantic ve que un campo es SecretStr, lo envuelve en una "caja de seguridad".
Si se intenta imprimirlo o guardarlo directamente, se verá **********.
Para sacar el string real y pasárselo a una función, se abre la caja con el método get_secret_value().
'''

class UserLogin(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: SecretStr = Field(..., min_length=8, max_length=128)

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

class ChangePassword(BaseModel):
    old_password: SecretStr = Field(..., min_length=8, max_length=128)
    new_password: SecretStr = Field(..., min_length=8, max_length=128)

    @field_validator("old_password", "new_password", mode="after")
    @classmethod
    def validar_password(cls, value: SecretStr) -> SecretStr:

        validate_password(value.get_secret_value())
        return value

    model_config = ConfigDict(from_attributes=True)

class ForgotPasswordEmail(BaseModel):
    email: EmailStr = Field(..., max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    model_config = ConfigDict(from_attributes=True)

class ResetPasswordEmail(BaseModel):
    token: constr(min_length=30, max_length=100)
    new_password: SecretStr = Field(..., min_length=8, max_length=128)

    @field_validator("new_password", mode="after")
    @classmethod
    def validar_password(cls, value: SecretStr) -> SecretStr:

        validate_password(value.get_secret_value())
        return value

    model_config = ConfigDict(from_attributes=True)

class FormaEnvio(str, Enum):
    sms = "sms"
    wpp = "wpp"

class ForgotPasswordMobile(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    telefono: Telefono
    forma: FormaEnvio # sms o wpp

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_email(cls, value: EmailStr) -> str:
        # Importante: .strip() elimina espacios invisibles
        return value.lower().strip()

    model_config = ConfigDict(from_attributes=True)

class ResetPasswordMobile(BaseModel):
    telefono: Telefono
    otp: constr(pattern=r"^\d{6}$") # numérico de 6 dígitos
    new_password: SecretStr = Field(..., min_length=8, max_length=128)

    @field_validator("new_password", mode="after")
    @classmethod
    def validar_password(cls, value: SecretStr) -> SecretStr:

        validate_password(value.get_secret_value())
        return value

    model_config = ConfigDict(from_attributes=True)