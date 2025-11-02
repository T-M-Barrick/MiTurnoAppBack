from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Time, Float, Numeric, Boolean, UniqueConstraint, func
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
    turnos = relationship("Turno", back_populates="usuario") # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Turno
    historial = relationship("Historial", back_populates="usuario") # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Historial
    miembro_empresas = relationship("Miembro_Empresa", back_populates="usuario")

class Empresa(Base):
    __tablename__ = "empresa"
    
    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(Integer, nullable=False)
    nombre = Column(String(100, collation=variables.COLLATION_MYSQL_8), nullable=False) # La collation hace que no distinga tildes y mayúsculas y minúsculas
    email = Column(String(100), nullable=False)
    rubro = Column(String(100))
    rubro2 = Column(String(100))
    calificacion = Column(Float(precision=2), default=0)

    # Relationships
    telefonos = relationship("Telefono", back_populates="empresa")
    direccion = relationship("Direccion", back_populates="empresa", uselist=False)
    servicios = relationship("Servicio", back_populates="empresa")
    disponibilidades = relationship("Emp_Disp", back_populates="empresa")
    calificaciones = relationship("Calificacion", back_populates="empresa") # Relación bidireccional de uno a muchos con la tabla Calificacion
    miembros = relationship("Miembro_Empresa", back_populates="empresa")

class Miembro_Empresa(Base):
    __tablename__ = "miembro_empresa"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), primary_key=True)
    rol = Column(String(50), nullable=False)  # 'propietario', 'gerente' o 'empleado'

    __table_args__ = (UniqueConstraint("usuario_id", "empresa_id", name="uq_m_e_usuario_empresa"), )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_empresas")
    empresa = relationship("Empresa", back_populates="miembros")

class Telefono(Base):

    __tablename__ = "telefono"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id")) # Relación muchos a uno con la tabla usuario (un usuario puede tener varios teléfonos)
    empresa_id = Column(Integer, ForeignKey("empresa.id")) # Relación muchos a uno con la tabla empresa (una empresa puede tener varios teléfonos)

    # Relationships
    usuario = relationship("Usuario", back_populates="telefonos")
    empresa = relationship("Empresa", back_populates="telefonos")

class Direccion(Base):
    __tablename__ = "direccion"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id")) # NULL si pertenece a un usuario. Por defecto es nullable=True
    domicilio = Column(String(255)) # El devuelto por Google Maps
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    piso = Column(String(50))
    departamento = Column(String(50))
    aclaracion = Column(String(255))

    # Relationships
    empresa = relationship("Empresa", back_populates="direccion")

class Dir_Usuario(Base):
    __tablename__ = "direccion_usuario"

    direccion_id = Column(Integer, ForeignKey("direccion.id"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)

class Turno(Base):
    __tablename__ = "turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    nombre_de_servicio = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración como con quién quiere atenderse el usuario
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno_usuario.id"), nullable=False)
    estado_turno_empresa_id = Column(Integer, ForeignKey("estado_turno_empresa.id"), nullable=False)
    eliminado = Column(String(50)) # NULL si nadie lo movió a su historial. 'u' si lo movió a su historial el usuario. 'e' si lo movió a su historial la empresa. 

    # Relationships
    usuario = relationship("Usuario", back_populates="turno")
    empresa = relationship("Empresa")
    estado_turno_usuario = relationship("Estado_Turno_Usuario")
    estado_turno_empresa = relationship("Estado_Turno_Empresa")

class Historial(Base):
    __tablename__ = "historial_turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    nombre_de_servicio = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración como con quién quiere atenderse el usuario

    # Al pasar a Historial, sin que lo haga el limpiador periódico, el estado del otro va a ser ser NULL y así cuando el usuario o empresa
    # pida su historial, no se van a pasar los que tengan NULL en su estado ya que significa que nunca eliminaron al turno.
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno_usuario.id"))
    estado_turno_empresa_id= Column(Integer, ForeignKey("estado_turno_empresa.id"))

    # Relationships
    usuario = relationship("Usuario", back_populates="historial_turno")
    empresa = relationship("Empresa")
    estado_turno_usuario = relationship("Estado_Turno_Usuario")
    estado_turno_empresa = relationship("Estado_Turno_Empresa")

class Servicio(Base):
    __tablename__ = "servicio"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    duracion = Column(Integer) # minutos
    precio = Column(Numeric(10, 2))  # 10 dígitos, 2 decimales
    aclaracion = Column(String(255)) # cualquier aclaración como con quién quiere atenderse el usuario

    # Relationships
    empresa = relationship("Empresa", back_populates="servicios")

class Estado_Turno_Usuario(Base):
    __tablename__ = "estado_turno_usuario" # Esta tabla ya viene con estados puestos

    id = Column(Integer, primary_key=True)
    estado = Column(String(50), unique=True, nullable=False)

class Estado_Turno_Empresa(Base):
    __tablename__ = "estado_turno_empresa" # Esta tabla ya viene con estados puestos

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

class Emp_Disp(Base): # Conecta Empresa con Disponibiliad
    __tablename__ = "empresa_disponibilidad"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"))
    disponibilidad_id = Column(Integer, ForeignKey("disponibilidad.id"))

    __table_args__ = (UniqueConstraint("empresa_id", "disponibilidad_id", name="uq_emp_disp_empresa_id_disponibilidad_id"), )

    # Relationships
    empresa = relationship("Empresa", back_populates="disponibilidades")
    disponibilidad = relationship("Disponibilidad")
    servicios = relationship("Emp_Disp_Ser", back_populates="emp_disp")

class Emp_Disp_Ser(Base): # Conecta Emp_Disp con Servicio
    __tablename__ = "empresa_disponibilidad_servicio"

    emp_disp_id = Column(Integer, ForeignKey("empresa_disponibilidad.id"), primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicio.id"), primary_key=True)
    cant_turnos_max = Column(Integer)

    # Relationships
    emp_disp = relationship("Emp_Disp", back_populates="servicios")
    servicio = relationship("Servicio")

class Calificacion(Base):
    __tablename__ = "calificacion"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    valor = Column(Integer, nullable=False)  # 0-10

    # Relationships
    empresa = relationship("Empresa", back_populates="calificaciones")

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
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)
