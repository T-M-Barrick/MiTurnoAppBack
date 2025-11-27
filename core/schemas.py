from datetime import datetime, date, time
from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field, conint, validator

# ------------------ SCHEMAS USUARIOS Y EMPRESAS ------------------ #

class TurnoUpdate(BaseModel):
    id: int
    estado_turno: str

    model_config = {"from_attributes": True}

class DireccionIn(BaseModel):
    domicilio: str
    lat: float
    lng: float
    aclaracion: Optional[str] = None

    model_config = {"from_attributes": True}

class DireccionOut(BaseModel):
    id: int
    domicilio: str
    lat: float
    lng: float
    aclaracion: Optional[str] = None

    model_config = {"from_attributes": True}

class DireccionUpdate(BaseModel):
    id: int
    domicilio: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    aclaracion: Optional[str] = None

    model_config = {"from_attributes": True}

# ------------------ SCHEMAS USUARIOS ------------------ #

class UserCreate(BaseModel):
    dni: int
    apellido: str
    nombre: str
    email: str
    password: str
    telefonos: list[int] = Field(default_factory=list)
    direcciones: list[DireccionIn] # obligatorio al crear su usuario

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
    rubro: Optional[str] = None
    rubro2: Optional[str] = None
    calificacion: Optional[int] = None
    telefonos: list[int] = Field(default_factory=list)
    direccion: DireccionOut
    logo: Optional[str] = None

    model_config = {"from_attributes": True}

class TurnoOut(BaseModel):
    id: int
    empresa: str
    logo_empresa: Optional[str] = None
    direccion: DireccionOut
    fecha_hora: datetime
    nombre_de_servicio: str
    duracion: Optional[int] = None
    precio: Optional[Decimal] = None
    aclaracion_de_servicio: Optional[str] = None
    profesional_dni: Optional[int] = None
    profesional_apellido: Optional[str] = None
    profesional_nombre: Optional[str] = None
    estado_turno: str

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
    nombre: str # Nombre de la empresa
    
    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    dni: Optional[int] = None
    apellido: Optional[str] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    telefonos: Optional[list[list[int]]] = None
    direcciones: Optional[list[DireccionUpdate]] = None
    favoritos: Optional[list[int]] = None

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
    duracion: Optional[int] = None
    precio: Optional[Decimal] = None
    aclaracion_de_servicio: Optional[str] = None
    profesional_dni: Optional[int] = None
    profesional_apellido: Optional[str] = None
    profesional_nombre: Optional[str] = None
    estado_turno: str

    model_config = {"from_attributes": True}

class HistorialResponse(BaseModel):
    historial: list[HistorialOut] = Field(default_factory=list)
    ultimo_cursor: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ReservaTurnoIn(BaseModel):
    empresa_id: int
    fecha_hora: datetime
    servicio_id: int # en caso de que hayan muchos servicios iguales con distintos profesionales, el front va a mandar el id de cualquiera de esos servicios
    profesional_id: Optional[int] = None # si es 0, entonces significa que es un servicio que tiene profesionales pero que al cliente le da igual cuál

    model_config = {"from_attributes": True}

class TurnoReservadoOut(BaseModel):
    message: str
    turno: Optional[TurnoOut] = None

    model_config = {"from_attributes": True}

class Calificacion(BaseModel):
    empresa_id: int
    valor: conint(ge=0, le=10)  # solo permite enteros de 0 a 10

    model_config = {"from_attributes": True}

# ------------------ SCHEMAS EMPRESAS ------------------ #

class EmpresaCreate(BaseModel):
    cuit: int
    nombre: str
    email: str
    rubro: Optional[str] = None
    rubro2: Optional[str] = None
    telefonos: list[int] = Field(default_factory=list)
    direccion: DireccionIn # obligatorio al crear su empresa
    logo: Optional[str] = None  # <-- string Base64

    model_config = {"from_attributes": True}

class EmpresaUpdate(BaseModel):
    cuit: Optional[int] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    rubro: Optional[str] = None
    rubro2: Optional[str] = None
    telefonos: Optional[list[list[int]]] = None  # [[id, numero], ...]
    direccion: Optional[DireccionUpdate] = None
    logo: Optional[str] = None

    model_config = {"from_attributes": True}

class HistorialEmpresaOut(BaseModel):
    usuario_dni: int
    usuario_apellido: str
    usuario_nombre: str
    fecha_hora: datetime
    nombre_de_servicio: str
    duracion: Optional[int] = None
    precio: Optional[Decimal] = None
    aclaracion_de_servicio: Optional[str] = None
    profesional_dni: Optional[int] = None
    profesional_apellido: Optional[str] = None
    profesional_nombre: Optional[str] = None
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
    nombre_de_servicio: str
    duracion: Optional[int] = None
    precio: Optional[Decimal] = None
    aclaracion_de_servicio: Optional[str] = None
    profesional_dni: Optional[int] = None
    profesional_apellido: Optional[str] = None
    profesional_nombre: Optional[str] = None
    estado_turno: str

    model_config = {"from_attributes": True}

class UserOut(BaseModel):
    id: int
    dni: int
    apellido: str
    nombre: str
    email: str
    rol: str  # rol dentro de la empresa

    model_config = {"from_attributes": True}

class DisponibilidadOut(BaseModel):
    id: int
    dia: str
    hora: str # para el output, JSON no reconoce el tipo time y por eso se lo envía como string
    cant_turnos_max: int

    model_config = {"from_attributes": True}

class ServicioOut(BaseModel):
    id: int
    nombre: str
    duracion: Optional[int] = None
    precio: Optional[Decimal] = None
    aclaracion: Optional[str] = None
    profesional_id: Optional[int] = None
    profesional_dni: Optional[int] = None
    profesional_apellido: Optional[str] = None
    profesional_nombre: Optional[str] = None
    disponibilidades: list[DisponibilidadOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}

class EmpresaPanelOut(BaseModel):
    id: int
    cuit: int
    nombre: str
    email: str
    rubro: Optional[str] = None
    rubro2: Optional[str] = None
    calificacion: Optional[int] = None
    telefonos: list[list[int]] = Field(default_factory=list)
    direccion: DireccionOut
    logo: Optional[str] = None
    servicios: list[ServicioOut]
    turnos: list[TurnoEmpresaOut] = Field(default_factory=list)
    miembros: list[UserOut] = Field(default_factory=list)
    rol: str

    model_config = {"from_attributes": True}

class InvitacionEmpleadoIn(BaseModel):
    usuario_email: str
    rol: str

    model_config = {"from_attributes": True}

class ModificarRolIn(BaseModel):
    usuario_id: int # ID del usuario al que se le cambia el rol
    nuevo_rol: str # nuevo rol ('gerente', 'supervisor', 'empleado', etc.)

    model_config = {"from_attributes": True}

class EliminarMiembroIn(BaseModel):
    usuario_id: int

    model_config = {"from_attributes": True}

class DisponibilidadServicio(BaseModel):
    dia: str # Ej: "Lunes"
    hora_inicio: time
    hora_fin: time
    cant_turnos_max: int

    @validator("hora_inicio", "hora_fin")
    def validar_hora_5min(cls, v: time):
        if v.minute % 5 != 0:
            raise ValueError("La hora debe ser múltiplo de 5 minutos")
        return v

    @validator("hora_fin")
    def validar_fin_mayor_inicio(cls, v: time, values):
        if "hora_inicio" in values and v <= values["hora_inicio"]:
            raise ValueError("hora_fin debe ser mayor que hora_inicio")
        return v
    
    model_config = {"from_attributes": True}

# Este schema sirve tanto para actualizar un servicio existente como para crearlo (por eso el id es opcional)
class ServicioUpdate(BaseModel):
    id: Optional[int] = None # Si se quiere actualizar uno existente
    nombre: str
    duracion: int
    precio: float
    aclaracion: Optional[str] = None
    profesional_id: Optional[int] = None
    disponibilidades: list[DisponibilidadServicio] = Field(default_factory=list) # Lista de disponibilidades por días (lista de mínimo 7 elementos)
    
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

class ServiciosUpdateIn(BaseModel):
    servicios: list[ServicioUpdate]
    
    model_config = {"from_attributes": True}

class ServiciosDeleteIn(BaseModel):
    servicios: list[int] # IDs de servicios a eliminar

    model_config = {"from_attributes": True}