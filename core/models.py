from datetime import datetime, timedelta

from sqlalchemy import (Column, Integer, BigInteger, LargeBinary, String, ForeignKey, 
    DateTime, Date, Time, Float, Numeric, Boolean, UniqueConstraint, func)
from sqlalchemy.orm import relationship

from core.database import Base
from core import variables

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True) # Al ser PK simple con Integer, SQLAlchemy sobreentiende que autoincrement=True y no es necesario ponerlo
    dni = Column(Integer, nullable=False)
    apellido = Column(String(50), nullable=False) # nullable=False es NOT NULL
    nombre = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # Relationships
    telefonos = relationship("Telefono", back_populates="usuario") # Relación bidireccional gracias a back_populates
    direcciones = relationship("Direccion", secondary="direccion_usuario") # Relación unidireccional de muchos a muchos con la tabla Direccion
    favoritos = relationship("Empresa", secondary="favorito") # Relación unidireccional de muchos a muchos con la tabla Empresa

    turnos = relationship(
        "Turno",
        back_populates="usuario",
        foreign_keys="[Turno.usuario_id]"  # 🔹 Turnos donde actúa como cliente
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Turno
    profesional_turnos = relationship(
        "Turno",
        back_populates="profesional",
        foreign_keys="[Turno.profesional_id]"  # 🔹 Turnos donde actúa como profesional
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Turno

    historial = relationship(
        "Historial",
        back_populates="usuario",
        foreign_keys="[Historial.usuario_id]"  # 🔹 Turnos donde actuó como cliente
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Historial
    profesional_historial = relationship(
        "Historial",
        back_populates="profesional",
        foreign_keys="[Historial.profesional_id]"  # 🔹 Turnos donde actuó como profesional
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Historial

    miembro_empresas = relationship("Miembro_Empresa", back_populates="usuario")

class Empresa(Base):
    __tablename__ = "empresa"
    
    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(BigInteger, nullable=False)
    nombre = Column(String(100, collation=variables.COLLATION_MYSQL_8), nullable=False) # La collation hace que no distinga tildes y mayúsculas y minúsculas
    email = Column(String(100), nullable=False)
    rubro = Column(String(100))
    rubro2 = Column(String(100))
    calificacion = Column(Float(precision=2), default=0)
    logo =  Column(LargeBinary)

    # Relationships
    telefonos = relationship("Telefono", back_populates="empresa")
    direccion = relationship("Direccion", back_populates="empresa", uselist=False)
    servicios = relationship("Servicio", back_populates="empresa")
    calificaciones = relationship("Calificacion", back_populates="empresa") # Relación bidireccional de uno a muchos con la tabla Calificacion
    miembros = relationship("Miembro_Empresa", back_populates="empresa")

class Miembro_Empresa(Base):
    __tablename__ = "miembro_empresa"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    rol = Column(String(50), nullable=False)  # 'propietario', 'gerente' o 'empleado'

    __table_args__ = (UniqueConstraint("usuario_id", "empresa_id", name="uq_m_e_usuario_empresa"), )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_empresas")
    empresa = relationship("Empresa", back_populates="miembros")
    servicios = relationship("Servicio", back_populates="profesional")

class Telefono(Base):

    __tablename__ = "telefono"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(BigInteger, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True) # Relación muchos a uno con la tabla usuario (un usuario puede tener varios teléfonos)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True) # Relación muchos a uno con la tabla empresa (una empresa puede tener varios teléfonos)

    # Relationships
    usuario = relationship("Usuario", back_populates="telefonos")
    empresa = relationship("Empresa", back_populates="telefonos")

class Direccion(Base):
    __tablename__ = "direccion"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True) # NULL si pertenece a un usuario
    calle = Column(String(255))
    altura = Column(String(255))
    localidad = Column(String(255))
    departamento = Column(String(255))
    provincia = Column(String(255))
    pais = Column(String(255))
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    aclaracion = Column(String(255))

    # Relationships
    empresa = relationship("Empresa", back_populates="direccion")

class Dir_Usuario(Base):
    __tablename__ = "direccion_usuario"

    direccion_id = Column(Integer, ForeignKey("direccion.id"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)

    # Relationships
    direccion = relationship("Direccion")

class Turno(Base):
    __tablename__ = "turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    servicio_id = Column(Integer, nullable=False)
    nombre_de_servicio = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno.id"), nullable=False)
    estado_turno_empresa_id = Column(Integer, ForeignKey("estado_turno.id"), nullable=False)
    eliminado = Column(String(50)) # NULL si nadie lo movió a su historial. 'u' si lo movió a su historial el usuario. 'e' si lo movió a su historial la empresa.
    recordatorio_id = Column(Integer, ForeignKey("recordatorio.id"), nullable=True)

    # Relationships
    usuario = relationship(
        "Usuario",
        back_populates="turnos",
        foreign_keys=[usuario_id]  # 🔹 indica que esta relación usa usuario_id
    )
    profesional = relationship(
        "Usuario",
        back_populates="profesional_turnos",
        foreign_keys=[profesional_id]  # 🔹 indica que esta relación usa profesional_id
    )

    empresa = relationship("Empresa")

    estado_turno_usuario = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_usuario_id]
    )

    estado_turno_empresa = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_empresa_id]
    )

    recordatorio = relationship("Recordatorio", back_populates="turnos")

class Historial(Base):
    __tablename__ = "historial_turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    nombre_de_servicio = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)

    # Al pasar a Historial, sin que lo haga el limpiador periódico, el estado del otro va a ser ser NULL y así cuando el usuario o empresa
    # pida su historial, no se van a pasar los que tengan NULL en su estado ya que significa que nunca eliminaron al turno.
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno.id"))
    estado_turno_empresa_id = Column(Integer, ForeignKey("estado_turno.id"))

    # Relationships
    usuario = relationship(
        "Usuario",
        back_populates="historial",
        foreign_keys=[usuario_id]  # 🔹 indica que esta relación usa usuario_id
    )
    profesional = relationship(
        "Usuario",
        back_populates="profesional_historial",
        foreign_keys=[profesional_id]  # 🔹 indica que esta relación usa profesional_id
    )
    
    empresa = relationship("Empresa")

    estado_turno_usuario = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_usuario_id]
    )

    estado_turno_empresa = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_empresa_id]
    )

class Servicio(Base):
    __tablename__ = "servicio"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion = Column(String(255)) # cualquier aclaración o descripción
    miembro_empresa_id = Column(Integer, ForeignKey("miembro_empresa.id"), nullable=True)

    # Relationships
    empresa = relationship("Empresa", back_populates="servicios")
    profesional = relationship("Miembro_Empresa", back_populates="servicios")
    ser_disps = relationship("Ser_Disp", back_populates="servicio")
    disponibilidades = relationship("Disponibilidad2", back_populates="servicio")

class Estado_Turno(Base):
    __tablename__ = "estado_turno" # Esta tabla ya viene con estados puestos

    id = Column(Integer, primary_key=True)
    estado = Column(String(50), unique=True, nullable=False)

class Favorito(Base):
    __tablename__ = "favorito"

    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), primary_key=True)

class Disponibilidad(Base):
    __tablename__ = "disponibilidad" # Esta tabla ya viene con los días y horarios puestos

    id = Column(Integer, primary_key=True)
    dia = Column(String(50), nullable=False)
    hora = Column(Time, nullable=False) # cada 5 minutos

    __table_args__ = (UniqueConstraint("dia", "hora", name="uq_disponibilidad_dia_hora"), )

class Disponibilidad2(Base):
    __tablename__ = "disponibilidad2"

    id = Column(Integer, primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicio.id"), nullable=False)
    dia = Column(String(50), nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    intervalo = Column(Integer, nullable=False) # múltiplo de 5 minutos
    cant_turnos_max = Column(Integer)

    # Relationships
    servicio = relationship("Servicio", back_populates="disponibilidades")

class Ser_Disp(Base): # Conecta Servicio con Disponibilidad
    __tablename__ = "servicio_disponibilidad"

    servicio_id = Column(Integer, ForeignKey("servicio.id"), primary_key=True)
    disponibilidad_id = Column(Integer, ForeignKey("disponibilidad.id"), primary_key=True)
    cant_turnos_max = Column(Integer)

    # Relationships
    servicio = relationship("Servicio", back_populates="ser_disps")
    disponibilidad = relationship("Disponibilidad")

class Calificacion(Base):
    __tablename__ = "calificacion"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    valor = Column(Integer, nullable=False)  # 0-10

    # Relationships
    empresa = relationship("Empresa", back_populates="calificaciones")

class Recordatorio(Base):
    __tablename__ = "recordatorio"

    id = Column(Integer, primary_key=True, index=True)
    minutos_antes = Column(Integer, nullable=False)

    # Relationships
    turnos = relationship("Turno", back_populates="recordatorio")

class OTPCode(Base):
    __tablename__ = "otp_code"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

class Token(Base):
    __tablename__ = "token_password"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))

class Blacklist(Base):
    __tablename__ = "blacklist_token"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)