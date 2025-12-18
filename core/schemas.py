from datetime import datetime, date, time
from typing import Optional # Optional[X] --> el valor puede ser X o puede ser None
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, conint, field_validator, model_validator

# ------------------ SCHEMAS USUARIOS Y EMPRESAS ------------------ #

class TurnoUpdate(BaseModel):
    id: int
    estado_turno: str | None
    recordatorio: int | None # minutos antes

    @field_validator("recordatorio")
    def validar_recordatorio(cls, value):
        if value is None:
            return value  # Es opcional, no validar si no lo envían

        # 23:30 en minutos
        MAX_MINUTOS = 23 * 60 + 30  # 1410

        if value < 0 or value > MAX_MINUTOS:
            raise ValueError("El recordatorio debe estar entre 0 y 1410 minutos (23:30)")

        if value % 30 != 0:
            raise ValueError("El recordatorio debe ser múltiplo de 30 minutos")

        return value

    model_config = {"from_attributes": True}

class TurnoEstadoOut(BaseModel):
    id: int
    estado: str

    model_config = {"from_attributes": True}

class DireccionIn(BaseModel):
    calle: str | None
    altura: str | None
    localidad: str | None
    departamento: str | None
    provincia: str | None
    pais: str | None
    lat: float
    lng: float
    aclaracion: str | None

    model_config = {"from_attributes": True}

class DireccionOut(BaseModel):
    id: int
    calle: str | None
    altura: str | None
    localidad: str | None
    departamento: str | None
    provincia: str | None
    pais: str | None
    lat: float
    lng: float
    aclaracion: str | None

    model_config = {"from_attributes": True}

class DireccionUpdate(BaseModel):
    '''
    Todos los campos son obligatorios de enviar en este schema.
    Que en un campo se envíe None significa que se actualiza ese atributo en la base como NULL
    '''
    id: int
    calle: str | None
    altura: str | None
    localidad: str | None
    departamento: str | None
    provincia: str | None
    pais: str | None
    lat: float
    lng: float
    aclaracion: str | None

    model_config = {"from_attributes": True}

class DisponibilidadOut(BaseModel):
    id: int
    dia: str
    hora: str # para el output, JSON no reconoce el tipo time y por eso se lo envía como string
    cant_turnos_max: int

    model_config = {"from_attributes": True}

# Este schema se usa en los endpoints users/verificacion_email y empresas/aceptar_rol
class TokenRequest(BaseModel):
    token: str

    model_config = {"from_attributes": True}

# ------------------ SCHEMAS USUARIOS ------------------ #

class UserCreate(BaseModel):
    dni: int
    apellido: str
    nombre: str
    email: str
    password: str
    telefonos: list[int]
    direcciones: list[DireccionIn]

    # ❗ No permitir lista vacía en teléfonos
    @field_validator("telefonos")
    def validar_telefonos_no_vacio(cls, v):
        if v == []:
            raise ValueError('''Debido a que un usuario no puede no tener ningún teléfono asociado, 
                debe enviar al menos un teléfono o no enviar el campo.''')
        return v

    # ❗ No permitir lista vacía en direcciones
    @field_validator("direcciones")
    def validar_direcciones_no_vacio(cls, v):
        if v == []:
            raise ValueError('''Debido a que un usuario no puede no tener ninguna dirección asociada, 
                debe enviar al menos una dirección o no enviar el campo.''')
        return v

    model_config = {"from_attributes": True}

class UserLogin(BaseModel):
    email: str
    password: str
    
    model_config = {"from_attributes": True}

class EmpresaOut(BaseModel):
    id: int
    cuit: int
    nombre: str
    email: str
    rubro: str | None
    rubro2: str | None
    calificacion: str | None
    telefonos: list[int] = Field(default_factory=list)
    direccion: DireccionOut
    logo: str | None

    model_config = {"from_attributes": True}

class TurnoOut(BaseModel):
    id: int
    empresa_id: int
    empresa: str
    logo_empresa: str | None
    direccion: DireccionOut
    fecha_hora: datetime
    nombre_de_servicio: str
    duracion: int | None
    precio: Decimal | None
    aclaracion_de_servicio: str | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    estado_turno: str
    recordatorio: int | None

    model_config = {"from_attributes": True}

class UserLoginOut(BaseModel):
    id: int
    dni: int
    apellido: str
    nombre: str
    email: str
    telefonos: list[list[int]] = Field(default_factory=list)
    direcciones: list[DireccionOut]
    favoritos: list[EmpresaOut] = Field(default_factory=list)
    turnos: list[TurnoOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class RolEmpresaOut(BaseModel):
    rol: str
    empresa_id: int
    nombre_empresa: str
    logo_empresa: str | None
    
    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    '''
    Que en un campo se envíe None o no se envíe el campo directamente, significa que no se actualiza ese campo.
    No significa, por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL o se borre.
    '''
    dni: Optional[int] = None
    apellido: Optional[str] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    telefonos: Optional[list[list[int]]] = None 
    direcciones: Optional[list[DireccionUpdate]] = None
    favoritos: Optional[list[int]] = None # Si la lista viene vacía, se borran todas las empresas favoritas

    # ❗ No permitir lista vacía en teléfonos
    @field_validator("telefonos")
    def validar_telefonos_no_vacio(cls, v):
        if v == []:
            raise ValueError('''Debido a que un usuario no puede no tener ningún teléfono asociado, 
                debe enviar al menos un teléfono o no enviar el campo.''')
        return v

    # ❗ No permitir lista vacía en direcciones
    @field_validator("direcciones")
    def validar_direcciones_no_vacio(cls, v):
        if v == []:
            raise ValueError('''Debido a que un usuario no puede no tener ninguna dirección asociada, 
                debe enviar al menos una dirección o no enviar el campo.''')
        return v


    model_config = {"from_attributes": True}

class UserUpdateOut(BaseModel):
    id: int
    dni: int
    apellido: str
    nombre: str
    email: str
    telefonos: list[list[int]] = Field(default_factory=list)
    direcciones: list[DireccionOut]
    favoritos: list[EmpresaOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class HistorialOut(BaseModel):
    empresa: str
    fecha_hora: datetime
    nombre_de_servicio: str
    duracion: int | None
    precio: Decimal | None
    aclaracion_de_servicio: str | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    estado_turno: str

    model_config = {"from_attributes": True}

class HistorialResponse(BaseModel):
    historial: list[HistorialOut] = Field(default_factory=list)
    ultimo_cursor: datetime | None

    model_config = {"from_attributes": True}

class ReservaTurnoIn(BaseModel):
    empresa_id: int
    fecha_hora: datetime
    servicio_id: int # en caso de que hayan muchos servicios iguales con distintos profesionales, el front va a mandar el id de cualquiera de esos servicios
    profesional_id: int | None # si es 0, entonces significa que es un servicio que tiene profesionales pero que al cliente le da igual cuál

    model_config = {"from_attributes": True}

class TurnoReservadoOut(BaseModel):
    message: str
    turno: Optional[TurnoOut] = None

    model_config = {"from_attributes": True}

class TurnoActualDelServicio(BaseModel):
    id: int
    fecha_hora: datetime
    duracion: int # minutos

    model_config = {"from_attributes": True}

class ServicioConTurnosOut(BaseModel):
    id: int
    nombre: str
    duracion: int | None
    precio: Decimal | None
    aclaracion: str | None
    profesional_id: int | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    disponibilidades: list[DisponibilidadOut] = Field(default_factory=list)
    turnos_actuales: list[TurnoActualDelServicio] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class Calificacion(BaseModel):
    empresa_id: int
    valor: conint(ge=0, le=10)  # solo permite enteros de 0 a 10

    model_config = {"from_attributes": True}

class ForgotPassword(BaseModel):
    email: EmailStr
    numero: int
    forma: str # sms o wpp

    model_config = {"from_attributes": True}

class ResetPassword(BaseModel):
    numero: int
    otp: str
    new_password: str

    model_config = {"from_attributes": True}

class ForgotPasswordEmail(BaseModel):
    email: EmailStr

    model_config = {"from_attributes": True}

class ResetPasswordEmail(BaseModel):
    token: str
    new_password: str

    model_config = {"from_attributes": True}

# ------------------ SCHEMAS EMPRESAS ------------------ #

class EmpresaCreate(BaseModel):
    cuit: int
    nombre: str
    email: str
    rubro: str | None
    rubro2: str | None
    telefonos: list[int] = Field(default_factory=list)
    direccion: DireccionIn # obligatorio al crear su empresa
    logo: str | None  # <-- string Base64

    model_config = {"from_attributes": True}

class EmpresaUpdate(BaseModel):
    '''
    Que en un campo se envíe None o no se envíe el campo directamente, significa que no se actualiza ese campo
    (esto no vale en el campo logo).
    No significa, por lo menos en este schema y sacando al campo logo, que si algo no se envía,
    entonces se cambie en la base a NULL o se borre.

    En el caso de logo, si el campo no se envía, entonces no se modifica, pero en caso de que sí se
    envíe y sea None, entonces se cambia el atributo en la tabla de la base por NULL (que el programa
    identifique si envió logo o lo envió como None se hace en la sección de "Actualizar campos simples"
    de la función crud.update_empresa en la parte que dice empresa_update.dict(exclude_unset=True)).
    '''
    cuit: Optional[int] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    rubro: Optional[str] = None
    rubro2: Optional[str] = None
    telefonos: Optional[list[list[int]]] = None  # [[id, numero], ...]. Si la lista viene vacía, se borran todos los teléfonos
    direccion: Optional[DireccionUpdate] = None
    logo: Optional[str] = None

class HistorialEmpresaOut(BaseModel):
    usuario_dni: int
    usuario_apellido: str
    usuario_nombre: str
    fecha_hora: datetime
    nombre_de_servicio: str
    duracion: int | None
    precio: Decimal | None
    aclaracion_de_servicio: str | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    estado_turno: str

    model_config = {"from_attributes": True}

class HistorialEmpresaResponse(BaseModel):
    historial: list[HistorialEmpresaOut] = Field(default_factory=list)
    ultimo_cursor: Optional[datetime] = None

    model_config = {"from_attributes": True}

class TurnoEmpresaOut(BaseModel):
    id: int
    usuario_dni: int
    usuario_apellido: str
    usuario_nombre: str
    fecha_hora: datetime
    servicio_id: int
    nombre_de_servicio: str
    duracion: int | None
    precio: Decimal | None
    aclaracion_de_servicio: str | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    estado_turno: str

    model_config = {"from_attributes": True}

class UserOut(BaseModel):
    id: int
    dni: int
    apellido: str
    nombre: str
    email: str
    rol: str # rol dentro de la empresa

    model_config = {"from_attributes": True}

class DisponibilidadServicio(BaseModel):
    dia: str # Ej: "Lunes"
    hora_inicio: time
    hora_fin: time
    intervalo: int
    cant_turnos_max: int

    @field_validator("hora_inicio", "hora_fin")
    @classmethod
    def validar_hora_5min(cls, v):
        if v.minute % 5 != 0:
            raise ValueError("La hora debe ser múltiplo de 5 minutos")
        return v
    
    @field_validator("intervalo")
    @classmethod
    def validar_intervalo_5min(cls, v):
        if v <= 0:
            raise ValueError("El intervalo debe ser mayor que 0")
        if v % 5 != 0:
            raise ValueError("El intervalo debe ser múltiplo de 5 minutos")
        return v
    
    @model_validator(mode="after")
    @classmethod
    def validar_consistencia(cls, values):
        inicio = values.hora_inicio
        fin = values.hora_fin
        intervalo = values.intervalo

        if fin < inicio:
            raise ValueError("hora_fin debe ser mayor o igual que hora_inicio")

        # convertir a minutos
        inicio_min = inicio.hour * 60 + inicio.minute
        fin_min = fin.hour * 60 + fin.minute
        duracion_total = fin_min - inicio_min

        if duracion_total % intervalo != 0:
            raise ValueError("hora_fin debe coincidir exactamente con múltiplos del intervalo desde hora_inicio")

        return values
    
    model_config = {"from_attributes": True}

class ServicioOut(BaseModel):
    id: int
    nombre: str
    duracion: int | None
    precio: Decimal | None
    aclaracion: str | None
    profesional_id: int | None
    profesional_dni: int | None
    profesional_apellido: str | None
    profesional_nombre: str | None
    disponibilidades: list[DisponibilidadServicio] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class EmpresaPanelOut(BaseModel):
    id: int
    cuit: int
    nombre: str
    email: str
    rubro: str | None
    rubro2: str | None
    calificacion: int | None
    telefonos: list[list[int]] = Field(default_factory=list)
    direccion: DireccionOut
    logo: str | None
    servicios: list[ServicioOut] = Field(default_factory=list)
    turnos: list[TurnoEmpresaOut] = Field(default_factory=list)
    miembros: list[UserOut] = Field(default_factory=list)
    rol: str

    model_config = {"from_attributes": True}

class InvitacionEmpleadoIn(BaseModel):
    usuario_email: str
    rol: str

    model_config = {"from_attributes": True}

class ModificarRolIn(BaseModel):
    nuevo_rol: str # nuevo rol ('propietario', 'gerente', 'empleado')

    model_config = {"from_attributes": True}

class ServicioCreate(BaseModel):
    nombre: str 
    duracion: int | None
    precio: float | None
    aclaracion: str | None
    profesional_id: int | None
    disponibilidades: list[DisponibilidadServicio] = Field(default_factory=list) # Lista de disponibilidades por días

class ServicioUpdate(BaseModel):
    '''
    Que no se envíe el campo, significa que no se actualiza ese campo (esto no vale en el campo disponibilidades).
    No significa, por lo menos en este schema, que si algo no se envía, entonces se cambie en la base a NULL.

    En el caso de dsiponibilidades, pydantic no va a dejar que el usuario envíe None en su campo.
    Si el campo no se envía, entonces no se modifica, pero en caso de que sí se envíe y sea
    una lista vacía, entonces se interpreta como que quiere borrar todas las disponibilidades
    para con ese servicio y se procede a borrarlas a todas (que el programa identifique si envió disponibilidades
    o lo envió como lista vacía se hace en la función crud.update_servicios_empresa en la parte que dice
    update_data = s.dict(exclude_unset=True)).

    Todo campo que se envíe como None, se cambia en la base a NULL salvo disponibilidades (que no acepta None) y nombre que 
    en la función en el crud se exige que si se envía, tiene que tener un valor distinto de "" y None.
    '''
    id: int # obligatorio
    nombre: Optional[str] = None
    duracion: Optional[int] = None
    precio: Optional[float] = None
    aclaracion: Optional[str] = None
    profesional_id: Optional[int] = None
    disponibilidades: list[DisponibilidadServicio] = Field(default_factory=list) # Lista de disponibilidades por días
    
    model_config = {"from_attributes": True}

'''
Formato JSON de ServicioUpdate:
{
    "id": 1,
    "nombre": "Corte",
    "duracion": 30,
    "precio": 100,
    "aclaracion": Servicio de corte de pelo,
    "profesional_id": 8,
    "disponibilidades": [
        {"dia": "Lunes", "hora_inicio": "09:00", "hora_fin": "11:00", "cant_max": 3}
    ]
}
'''

class ServiciosDeleteIn(BaseModel):
    servicios: list[int] # IDs de servicios a eliminar

    # ❗ No permitir lista vacía
    @field_validator("servicios")
    def validar_servicios_no_vacio(cls, v):
        if v == []:
            raise ValueError('Si se desea eliminar servicios, entonces no puede entregarse una lista vacía')
        return v

    model_config = {"from_attributes": True}