from sqlalchemy import (Column, Integer, String, SmallInteger, LargeBinary, ForeignKey, 
    DateTime, Date, Time, Float, Numeric, Boolean, UniqueConstraint, CheckConstraint, func)
from sqlalchemy.orm import relationship

from core.database import Base
from core import constantes

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, index=True) # Al ser PK simple con Integer, SQLAlchemy sobreentiende que autoincrement=True y no es necesario ponerlo
    dni = Column(String(8), nullable=False)
    apellido = Column(String(50), nullable=False) # nullable=False es NOT NULL
    nombre = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_verificado = (Boolean, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    recordatorio_minutos_antes = Column(SmallInteger)
    fecha_alta = Column(DateTime)

    __table_args__ = (
        CheckConstraint("dni REGEXP '^[0-9]{6,8}$'", name="ck_usuario_dni_6_a_8_digitos"),
        CheckConstraint("recordatorio_minutos_antes >= 0", name="ck_usuario_recordatorio_por_defecto")
    )

    # Relationships
    telefonos = relationship("Telefono", back_populates="usuario") # Relación bidireccional gracias a back_populates
    direcciones = relationship("Direccion", secondary="direccion_usuario") # Relación unidireccional de muchos a muchos con la tabla Direccion
    favoritos = relationship("Sucursal", secondary="favorito") # Relación unidireccional de muchos a muchos con la tabla Sucursal

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

    bloqueos_de_sucursales = relationship(
        "Sucursal_Bloqueo",
        back_populates="usuario",
        foreign_keys="[Sucursal_Bloqueo.usuario_id]"
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Sucursal_Bloqueo
    bloqueos_a_usuarios = relationship(
        "Sucursal_Bloqueo",
        back_populates="usuario_bloqueador",
        foreign_keys="[Sucursal_Bloqueo.created_by_id]"
    ) # Relación bidireccional gracias a back_populates de uno a muchos con la tabla Sucursal_Bloqueo

    miembro_empresas = relationship("Miembro_Empresa", back_populates="usuario")
    miembro_sucursales = relationship("Miembro_Sucursal", back_populates="usuario")
    servicios = relationship("Servicio", back_populates="profesional")

class Empresa(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(String(11), nullable=False)
    nombre = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=False) # La collation hace que no distinga tildes y mayúsculas y minúsculas
    email = Column(String(255), nullable=False)
    email_verificado = Column(Boolean, nullable=False)
    rubro = Column(String(100))
    rubro2 = Column(String(100))
    logo_url = Column(String(255))
    logo_public_id = Column(String(50))
    fecha_alta = Column(DateTime)

    __table_args__ = (
        CheckConstraint("cuit REGEXP '^[0-9]{11}$'", name="ck_empresa_cuit_11_digitos"),
    )

    # Relationships
    sucursales = relationship("Sucursal", back_populates="empresa")
    miembros = relationship("Miembro_Empresa", back_populates="empresa")

class Sucursal(Base):
    __tablename__ = "sucursal"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    nombre = Column(String(50))
    email = Column(String(255))
    email_verificado = Column(Boolean)
    calificacion = Column(Numeric(4, 2), default=0)
    activa = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("calificacion >= 0", name="ck_sucursal_calificacion_pos"),
    )

    # Relationships
    empresa = relationship("Empresa", back_populates="sucursales")
    telefonos = relationship("Telefono", back_populates="sucursal")
    direccion = relationship("Direccion", back_populates="sucursal", uselist=False)
    servicios = relationship("Servicio", back_populates="sucursal")
    calificaciones = relationship("Calificacion", back_populates="sucursal") # Relación bidireccional de uno a muchos con la tabla Calificacion
    miembros = relationship("Miembro_Sucursal", back_populates="sucursal")
    bloqueos = relationship("Sucursal_Bloqueo", back_populates="sucursal")

class Miembro_Empresa(Base):
    __tablename__ = "miembro_empresa"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False)
    rol = Column(SmallInteger, nullable=False) # 1: 'propietario' o 2: 'gerente_general'

    __table_args__ = (
        UniqueConstraint("usuario_id", "empresa_id", name="uq_m_e_usuario_empresa"),
        CheckConstraint("rol BETWEEN 1 AND 100", name="ck_rol_1_100"), # Hasta 100 por escalabilidad
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_empresas")
    empresa = relationship("Empresa", back_populates="miembros")

class Miembro_Sucursal(Base):
    __tablename__ = "miembro_sucursal"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    rol = Column(SmallInteger, nullable=False)  # 1: 'gerente' o 2: 'empleado'

    __table_args__ = (
        UniqueConstraint("usuario_id", "sucursal_id", name="uq_m_s_usuario_sucursal"),
        CheckConstraint("rol BETWEEN 1 AND 100", name="ck_rol_1_100"), # Hasta 100 por escalabilidad
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_sucursales")
    sucursal = relationship("Sucursal", back_populates="miembros")

class Telefono(Base):
    __tablename__ = "telefono"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(30), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True) # Relación muchos a uno con la tabla usuario (un usuario puede tener varios teléfonos)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=True) # Relación muchos a uno con la tabla sucursal (una sucursal puede tener varios teléfonos)

    __table_args__ = (
        CheckConstraint("length(numero) >= 7", name="ck_telefono_len"),
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="telefonos")
    sucursal = relationship("Sucursal", back_populates="telefonos")

class Direccion(Base):
    __tablename__ = "direccion"

    id = Column(Integer, primary_key=True, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=True) # NULL si pertenece a un usuario
    calle = Column(String(255))
    altura = Column(String(255))
    localidad = Column(String(255))
    departamento = Column(String(255))
    provincia = Column(String(255))
    pais = Column(String(255))
    lat = Column(Numeric(8, 6), nullable=False)
    lng = Column(Numeric(9, 6), nullable=False)
    aclaracion = Column(String(255))

    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_lat_range"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="ck_lng_range"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="direccion")

class Dir_Usuario(Base):
    __tablename__ = "direccion_usuario"

    direccion_id = Column(Integer, ForeignKey("direccion.id"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)

    __table_args__ = (UniqueConstraint("direccion_id", "usuario_id", name="uq_dir_us_direccion_usuario"), )

    # Relationships
    direccion = relationship("Direccion")

class Turno(Base):
    __tablename__ = "turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    servicio_id = Column(Integer, nullable=False)
    nombre_de_servicio = Column(String(100), nullable=False)
    duracion = Column(Integer, nullable=False) # minutos
    precio = Column(Numeric(10, 2), nullable=False) # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno.id"), nullable=False)
    estado_turno_sucursal_id = Column(Integer, ForeignKey("estado_turno.id"), nullable=False)
    eliminado = Column(String(1)) # NULL si nadie lo movió a su historial. 'u' si lo movió a su historial el usuario. 's' si lo movió a su historial la sucursal.
    recordatorio_minutos_antes = Column(SmallInteger)

    __table_args__ = (
        UniqueConstraint("usuario_id", "servicio_id", "fecha_hora", name="uq_turno_usuario_servicio_fecha"),
        CheckConstraint("servicio_id >= 1", name="ck_turno_servicio_id_pos"),
        CheckConstraint("duracion > 0", name="ck_turno_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_turno_precio_pos"),
        CheckConstraint("eliminado IS NULL OR eliminado IN ('u', 's')", name="ck_turno_eliminado"),
        CheckConstraint("recordatorio_minutos_antes >= 0", name="ck_turno_recordatorio"),
    )

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

    sucursal = relationship("Sucursal")

    estado_turno_usuario = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_usuario_id]
    )

    estado_turno_sucursal = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_sucursal_id]
    )

class Historial(Base):
    __tablename__ = "historial_turno"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    nombre_de_servicio = Column(String(100), nullable=False)
    duracion = Column(Integer, nullable=False) # minutos
    precio = Column(Numeric(10, 2), nullable=False) # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255)) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)

    # Al pasar a Historial, sin que lo haga el limpiador periódico, el estado del otro va a ser ser NULL y así cuando el usuario o sucursal
    # pida su historial, no se van a pasar los que tengan NULL en su estado ya que significa que nunca eliminaron al turno.
    estado_turno_usuario_id = Column(Integer, ForeignKey("estado_turno.id"))
    estado_turno_sucursal_id = Column(Integer, ForeignKey("estado_turno.id"))

    __table_args__ = (
        CheckConstraint("duracion > 0", name="ck_historial_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_historial_precio_pos"),
    )

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
    
    sucursal = relationship("Sucursal")

    estado_turno_usuario = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_usuario_id]
    )

    estado_turno_sucursal = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_sucursal_id]
    )

class Servicio(Base):
    __tablename__ = "servicio"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    duracion = Column(Integer, nullable=False) # minutos
    precio = Column(Numeric(10, 2), nullable=False)  # 10 dígitos, 2 decimales
    aclaracion = Column(String(255)) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    minutos_min_reserva = Column(Integer, default=10, nullable=False)
    dias_max_reserva = Column(Integer, default=None) # contando el día actual e incluyendo al día puesto como el último

    # si este atributo es True, significa que solo puede cancelar los turnos de un profesional el mismo profesional o un superior suyo
    cancelacion_limitada = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("sucursal_id", "nombre", "profesional_id", name="uq_servicio_sucursal_nombre_profesional"),
        # Lamentablemente la restricción UNIQUE en SQL permite 2 servicios de la misma sucursal con nombres
        # iguales y profesional NULL, por lo que si no tiene profesional, entonces profesional_id será igual a 1 apuntando
        # al primer usuario creado que va a representar al hecho de que un servicio no tenga profesional.
        CheckConstraint("duracion > 0", name="ck_servicio_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_servicio_precio_pos"),
        CheckConstraint("minutos_min_reserva >= 0", name="ck_servicio_minutos_min_reserva"),
        CheckConstraint(
            "dias_max_reserva >= 0", name="ck_servicio_dias_max_reserva"
        ), # puede ser 0 ya que quizás el admin quiso sacar temporalmente el servicio sin borrarlo
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="servicios")
    profesional = relationship("Usuario", back_populates="servicios")
    disponibilidades = relationship("Disponibilidad", back_populates="servicio", passive_deletes=True)

class Estado_Turno(Base):
    __tablename__ = "estado_turno" # Esta tabla ya viene con estados puestos

    id = Column(Integer, primary_key=True)
    estado = Column(String(50), unique=True, nullable=False)

class Favorito(Base):
    __tablename__ = "favorito"

    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), primary_key=True)

class Disponibilidad(Base):
    __tablename__ = "disponibilidad"

    id = Column(Integer, primary_key=True)
    servicio_id = Column(Integer, ForeignKey("servicio.id", ondelete="CASCADE"), nullable=False)
    dia = Column(SmallInteger, nullable=False) # 0 = lunes, 6 = domingo
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    intervalo = Column(Integer, nullable=False) # múltiplo de 5 minutos
    cant_turnos_max = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("servicio_id", "dia", "hora_inicio",
            "intervalo", name="uq_disponibilidad_servicio_dia_hora_inicio_intervalo"),
        CheckConstraint("dia BETWEEN 0 AND 6", name="ck_dia_semana_0_6"),
        CheckConstraint("hora_inicio <= hora_fin", name="ck_horario_valido"),
        CheckConstraint("intervalo > 0", name="ck_intervalo_pos"),
        CheckConstraint(
            "cant_turnos_max >= 0", name="ck_cant_turnos_max_pos"
        ), # puede ser 0 ya que quizás el admin quiso sacar temporalmente la disponibilidad para ese día en el servicio
    )

    # Relationships
    servicio = relationship("Servicio", back_populates="disponibilidades")

class Sucursal_Bloqueo(Base):
    __tablename__ = "sucursal_bloqueo"

    id = Column(Integer, primary_key=True, index=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("usuario.id"), nullable=False) # quién lo bloqueó
    motivo = Column(String(255))
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("usuario_id", "sucursal_id", name="uq_s_b_sucursal_usuario"),
    )

    # Relationships
    usuario = relationship(
        "Usuario",
        back_populates="bloqueos_de_sucursales",
        foreign_keys=[usuario_id]  # 🔹 indica que esta relación usa usuario_id
    )
    usuario_bloqueador = relationship(
        "Usuario",
        back_populates="bloqueos_a_usuarios",
        foreign_keys=[created_by_id]  # 🔹 indica que esta relación usa created_by_id
    )

    sucursal = relationship("Sucursal", back_populates="bloqueos")

class Calificacion(Base):
    __tablename__ = "calificacion"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    valor = Column(Integer, nullable=False)  # 0-10

    __table_args__ = (
        CheckConstraint("valor BETWEEN 0 AND 10", name="ck_calificacion_0_10"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="calificaciones")

class LimiteEmail(Base):
    __tablename__ = "limite_email"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), index=True, nullable=False)
    accion = Column(String(50), nullable=False)
    conteo = Column(Integer, nullable=False)
    inicio_ventana = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("email", "accion", name="uq_limite_email_email_accion"),
        CheckConstraint("conteo BETWEEN 1 AND 100", name="ck_limite_email_conteo_valido"),
    )

class OTPCode(Base):
    __tablename__ = "otp_code"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_otp_expira_despues"),
    )

class Token(Base):
    __tablename__ = "token_password"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_token_expira_despues"),
    )

class Blacklist(Base):
    __tablename__ = "blacklist_token"

    id = Column(Integer, primary_key=True)
    jti = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, index=True, nullable=False)
    revoked_at = Column(DateTime, nullable=False)

'''
Borrar:

class Empresa(Base):
    __tablename__ = "empresa"
    
    id = Column(Integer, primary_key=True, index=True)
    cuit = Column(String(11), nullable=False)
    nombre = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=False) # La collation hace que no distinga tildes y mayúsculas y minúsculas
    email = Column(String(255), nullable=False)
    email_verificado = (Boolean, nullable=False)
    rubro = Column(String(100))
    rubro2 = Column(String(100))
    calificacion = Column(Numeric(4, 2), default=0)
    logo_url = Column(String(255))
    logo_public_id = Column(String(50))
    fecha_alta = Column(DateTime)


    __table_args__ = (
        CheckConstraint("cuit REGEXP '^[0-9]{11}$'", name="ck_empresa_cuit_11_digitos"),
        CheckConstraint("calificacion >= 0", name="ck_empresa_calificacion_pos"),
    )

    # Relationships
    telefonos = relationship("Telefono", back_populates="empresa")
    direccion = relationship("Direccion", back_populates="empresa", uselist=False)
    servicios = relationship("Servicio", back_populates="empresa")
    calificaciones = relationship("Calificacion", back_populates="empresa") # Relación bidireccional de uno a muchos con la tabla Calificacion
    miembros = relationship("Miembro_Empresa", back_populates="empresa")
    bloqueos = relationship("Empresa_Bloqueo", back_populates="empresa")
'''