from sqlalchemy import (
    Column, Integer, String,
    SmallInteger, LargeBinary, ForeignKey,
    DateTime, Date, Time,
    Float, Numeric, Boolean,
    UniqueConstraint, Index, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from core.database import Base
from core import constantes

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True) # Al ser PK simple con Integer, SQLAlchemy sobreentiende que autoincrement=True y no es necesario ponerlo
    dni = Column(String(8), nullable=False)
    apellido = Column(String(50), nullable=False) # nullable=False es NOT NULL
    nombre = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    email_verificado = Column(Boolean, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    recordatorio_minutos_antes = Column(SmallInteger, nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("dni REGEXP '^[0-9]{6,8}$'", name="ck_usuario_dni_6_a_8_digitos"),
        CheckConstraint("recordatorio_minutos_antes >= 0", name="ck_usuario_recordatorio_por_defecto"),
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

    miembro_empresas = relationship("Miembro_Empresa", back_populates="usuario")
    miembro_sucursales = relationship("Miembro_Sucursal", back_populates="usuario")
    servicios_base = relationship("ServicioBase", back_populates="profesional")
    notificaciones = relationship("Notificacion", back_populates="usuario")

class Empresa(Base):
    __tablename__ = "empresa"

    id = Column(Integer, primary_key=True)
    cuit = Column(String(11), nullable=False)
    nombre = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=False) # La collation hace que no distinga tildes y mayúsculas y minúsculas
    email = Column(String(255), unique=True, nullable=False)
    email_verificado = Column(Boolean, nullable=False)
    rubro = Column(String(100, collation=constantes.COLLATION_MYSQL_8), nullable=True)
    rubro2 = Column(String(100, collation=constantes.COLLATION_MYSQL_8), nullable=True)
    logo_url = Column(String(255), nullable=True)
    logo_public_id = Column(String(50), nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("cuit REGEXP '^[0-9]{11}$'", name="ck_empresa_cuit_11_digitos"),
    )

    # Relationships
    sucursales = relationship("Sucursal", back_populates="empresa")
    miembros = relationship("Miembro_Empresa", back_populates="empresa")
    notificaciones = relationship("Notificacion", back_populates="empresa")

class Sucursal(Base):
    __tablename__ = "sucursal"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    nombre = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    email_verificado = Column(Boolean, nullable=True)
    reserva_publica_habilitada = Column(Boolean, nullable=False)
    calificacion = Column(Numeric(4, 2), nullable=True)
    activa = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("empresa_id", "nombre", name="uq_sucursal_empresa_nombre"),
        # Lamentablemente la restricción UNIQUE en SQL permite 2 sucursales de la misma empresa con nombres
        # NULL, por lo que si no viene con nombre, entonces deberemos chequear en el back primero antes
        # de modificar o crear una sucursal si ya existe una sucursal de la misma empresa con nombre NULL. cambiar
        CheckConstraint("calificacion BETWEEN 0 AND 10", name="ck_sucursal_calificacion_0_10"),
    )

    # Relationships
    empresa = relationship("Empresa", back_populates="sucursales")
    clientes = relationship("Cliente", back_populates="sucursal")
    telefonos = relationship("Telefono", back_populates="sucursal")
    direccion = relationship("Direccion", back_populates="sucursal", uselist=False)
    servicios_base = relationship("ServicioBase", back_populates="sucursal")
    miembros = relationship("Miembro_Sucursal", back_populates="sucursal")
    bloqueos = relationship("BloqueoSucursal", back_populates="sucursal")
    notificaciones = relationship("Notificacion", back_populates="sucursal")

class Cliente(Base):
    __tablename__ = "cliente_sucursal"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    dni = Column(String(8), nullable=False)
    apellido = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=False)
    nombre = Column(String(50, collation=constantes.COLLATION_MYSQL_8), nullable=False)
    email = Column(String(255, collation=constantes.COLLATION_MYSQL_8), nullable=False)
    telefono = Column(String(30), nullable=True)
    telefono2 = Column(String(30), nullable=True)
    observacion = Column(String(500, collation=constantes.COLLATION_MYSQL_8), nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=False)
    activo = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("sucursal_id", "email", name="uq_cliente_sucursal_email"),
        Index("sucursal_id", "activo", "id", name="ix_cliente_sucursal_activo_id"),
        CheckConstraint("dni REGEXP '^[0-9]{6,8}$'", name="ck_cliente_sucursal_dni_6_a_8_digitos"),
        CheckConstraint("length(telefono) >= 7", name="ck_cliente_sucursal_telefono_len"),
        CheckConstraint("length(telefono2) >= 7", name="ck_cliente_sucursal_telefono2_len"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="clientes")
    bloqueo = relationship("BloqueoSucursal", back_populates="cliente", uselist=False)

class Telefono(Base):
    __tablename__ = "telefono"

    id = Column(Integer, primary_key=True)
    numero = Column(String(30), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True) # Relación muchos a uno con la tabla usuario (un usuario puede tener varios teléfonos)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=True, index=True) # Relación muchos a uno con la tabla sucursal (una sucursal puede tener varios teléfonos)

    __table_args__ = (
        CheckConstraint("length(numero) >= 7", name="ck_telefono_numero_len"),
        CheckConstraint(
            "(usuario_id IS NOT NULL AND sucursal_id IS NULL) OR "
            "(usuario_id IS NULL AND sucursal_id IS NOT NULL)",
            name="ck_telefono_usuario_xor_sucursal"
        ),
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="telefonos")
    sucursal = relationship("Sucursal", back_populates="telefonos")

class Direccion(Base):
    __tablename__ = "direccion"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=True, index=True) # NULL si pertenece a un usuario
    calle = Column(String(255), nullable=True)
    altura = Column(String(255), nullable=True)
    localidad = Column(String(255), nullable=True)
    departamento = Column(String(255), nullable=True)
    provincia = Column(String(255), nullable=True)
    pais = Column(String(255), nullable=True)
    lat = Column(Numeric(8, 6), nullable=False)
    lng = Column(Numeric(9, 6), nullable=False)
    aclaracion = Column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_lat_range"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="ck_lng_range"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="direccion")

class Dir_Usuario(Base):
    __tablename__ = "direccion_usuario"

    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    direccion_id = Column(Integer, ForeignKey("direccion.id"), primary_key=True)

    # Relationships
    direccion = relationship("Direccion")

class Turno(Base):
    __tablename__ = "turno"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    servicio_id = Column(Integer, nullable=False) # apunta a la tabla Servicio
    nombre_de_servicio = Column(String(100), nullable=False)
    duracion = Column(Integer, nullable=False) # minutos
    precio = Column(Numeric(10, 2), nullable=False) # 10 dígitos, 2 decimales
    aclaracion_de_servicio = Column(String(255), nullable=True) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    estado_turno_usuario_id = Column(SmallInteger, ForeignKey("estado_turno.id"), nullable=False)
    estado_turno_sucursal_id = Column(SmallInteger, ForeignKey("estado_turno.id"), nullable=False)
    eliminado_por_usuario = Column(Boolean, nullable=False)
    eliminado_por_sucursal = Column(Boolean, nullable=False)
    recordatorio_fecha_hora = Column(DateTime, nullable=True)
    recordatorio_enviado = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("usuario_id", "servicio_id", "fecha_hora", name="uq_turno_usuario_servicio_fecha"),
        UniqueConstraint("cliente_id", "servicio_id", "fecha_hora", name="uq_turno_cliente_servicio_fecha"),
        Index("usuario_id", "eliminado_por_usuario", name="ix_turno_usuario_eliminado"),
        Index("sucursal_id", "eliminado_por_sucursal", name="ix_turno_sucursal_eliminado"),
        Index("servicio_id", "estado_turno_sucursal_id", name="ix_turno_servicio_estado_turno"),
        Index("profesional_id", "estado_turno_sucursal_id", name="ix_turno_profesional_estado_turno"),
        Index("recordatorio_fecha_hora", "recordatorio_enviado", "estado_turno_usuario_id", name="ix_turno_enviar_recordatorios"),
        CheckConstraint("servicio_id >= 1", name="ck_turno_servicio_id_pos"),
        CheckConstraint("duracion > 0", name="ck_turno_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_turno_precio_pos"),
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
    cliente = relationship("Cliente")

    estado_turno_usuario = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_usuario_id]
    )

    estado_turno_sucursal = relationship(
        "Estado_Turno",
        foreign_keys=[estado_turno_sucursal_id]
    )

    calificacion = relationship("Calificacion", back_populates="turno", uselist=False) # Relación bidireccional de uno a uno con la tabla Calificacion

class ServicioBase(Base):
    __tablename__ = "servicio_base"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    aclaracion = Column(String(255), nullable=True) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)
    minutos_min_reserva = Column(Integer, nullable=False)
    dias_max_reserva = Column(Integer, nullable=True) # contando el día actual e incluyendo al día puesto como el último
    # Si este atributo es True, significa que solo puede cancelar los turnos de un profesional el mismo profesional o un superior suyo
    cancelacion_limitada = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("sucursal_id", "nombre", "profesional_id", name="uq_servicio_sucursal_nombre_profesional"),
        # Lamentablemente la restricción UNIQUE en SQL permite 2 servicios de la misma sucursal con nombres
        # iguales y profesional NULL, por lo que si no tiene profesional, entonces deberemos chequear en el back
        # primero antes de modificar o crear un servicio si ya existe un servicio de la misma sucursal con nombre
        # igual y profesional NULL.
        CheckConstraint("minutos_min_reserva >= 0", name="ck_servicio_minutos_min_reserva"),
        CheckConstraint(
            "dias_max_reserva >= 0", name="ck_servicio_dias_max_reserva"
        ), # puede ser 0 ya que quizás el admin quiso sacar temporalmente el servicio sin borrarlo
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="servicios_base")
    profesional = relationship("Usuario", back_populates="servicios_base")
    servicios = relationship("Servicio", back_populates="servicio_base", passive_deletes=True)
    excepciones_fechas = relationship("ExcepcionFechaServicio", back_populates="servicio_base", passive_deletes=True)

class Servicio(Base):
    __tablename__ = "servicio"

    id = Column(Integer, primary_key=True)
    servicio_base_id = Column(Integer, ForeignKey("servicio_base.id", ondelete="CASCADE"), nullable=False)
    duracion = Column(Integer, nullable=False) # minutos
    precio = Column(Numeric(10, 2), nullable=False)  # 10 dígitos, 2 decimales
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False)
    modify_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # Hay que agregar las vigencias que no se superpongan para el mismo servicio_base_id. cambiar
        CheckConstraint("duracion > 0", name="ck_servicio_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_servicio_precio_pos"),
        CheckConstraint(
            "vigente_hasta IS NULL OR vigente_desde <= vigente_hasta", name="ck_servicio_fecha_franja_valida"
        ),
    )

    # Relationships
    servicio_base = relationship("ServicioBase", back_populates="servicios")
    disponibilidades = relationship("Disponibilidad", back_populates="servicio", passive_deletes=True)

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
        CheckConstraint(
            "intervalo > 0", name="ck_intervalo_pos"
        ), # si la dejo ser 0, después puede surgir problema cuando divida algo por este atributo intervalo
        CheckConstraint(
            "cant_turnos_max >= 0", name="ck_disponibilidad_cant_turnos_max_pos"
        ), # puede ser 0 ya que quizás el admin quiso sacar temporalmente la disponibilidad para ese día en el servicio
    )

    # Relationships
    servicio = relationship("Servicio", back_populates="disponibilidades")

class ExcepcionFechaServicio(Base):
    __tablename__ = "excepcion_fecha_servicio"

    id = Column(Integer, primary_key=True)
    servicio_base_id = Column(Integer, ForeignKey("servicio_base.id", ondelete="CASCADE"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    motivo = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("servicio_base_id", "fecha_inicio", name="uq_excepcion_servicio_fecha_franja"), # cambiar por superpos de intervalos
        CheckConstraint("fecha_inicio <= fecha_fin", name="ck_excepcion_fecha_franja_valida"),
    )

    servicio_base = relationship("ServicioBase", back_populates="excepciones_fechas")

class Miembro_Empresa(Base):
    __tablename__ = "miembro_empresa"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    rol_id = Column(SmallInteger, ForeignKey("rol.id"), nullable=False) # 1: 'PROPIETARIO' o 2: 'GERENTE_EMPRESA'

    __table_args__ = (
        UniqueConstraint("usuario_id", "empresa_id", name="uq_m_e_usuario_empresa"),
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_empresas")
    empresa = relationship("Empresa", back_populates="miembros")
    rol = relationship("Rol")

class Miembro_Sucursal(Base):
    __tablename__ = "miembro_sucursal"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False, index=True)
    rol_id = Column(SmallInteger, ForeignKey("rol.id"), nullable=False) # 3: 'GERENTE_SUCURSAL' o 4: 'EMPLEADO'

    __table_args__ = (
        UniqueConstraint("usuario_id", "sucursal_id", name="uq_m_s_usuario_sucursal"),
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="miembro_sucursales")
    sucursal = relationship("Sucursal", back_populates="miembros")
    rol = relationship("Rol")

class Favorito(Base):
    __tablename__ = "favorito"

    usuario_id = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), primary_key=True)

class BloqueoSucursal(Base):
    __tablename__ = "sucursal_bloqueo_cliente"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("usuario.id"), nullable=False) # quién lo bloqueó
    motivo = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("sucursal_id", "cliente_id", name="uq_s_b_sucursal_cliente"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="bloqueos")
    cliente = relationship("Cliente", back_populates="bloqueo")
    usuario_bloqueador = relationship("Usuario")

class Calificacion(Base):
    __tablename__ = "calificacion"

    id = Column(Integer, primary_key=True)
    turno_id = Column(Integer, ForeignKey("turno.id"), nullable=False, index=True)
    valor = Column(Integer, nullable=False) # 0-10

    __table_args__ = (
        CheckConstraint("valor BETWEEN 0 AND 10", name="ck_calificacion_0_10"),
    )

    # Relationships
    turno = relationship("Turno", back_populates="calificacion")

class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=True)
    tipo = Column(String(50), nullable=False)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False)
    leida = Column(Boolean, nullable=False)

    __table_args__ = (
        Index("usuario_id", "id", name="ix_notificacion_usuario_id_id"),
        Index("usuario_id", "empresa_id", "id", name="ix_notificacion_usuario_id_empresa_id_id"),
        Index("usuario_id", "sucursal_id", "id", name="ix_notificacion_usuario_id_sucursal_id_id"),
        CheckConstraint(
            "NOT (empresa_id IS NOT NULL AND sucursal_id IS NOT NULL)",
            name="ck_notificacion_empresa_sucursal"
        ),
    )

    # Relationships
    usuario = relationship("Usuario", back_populates="notificaciones")
    empresa = relationship("Empresa", back_populates="notificaciones")
    sucursal = relationship("Sucursal", back_populates="notificaciones")

class LimiteEmail(Base):
    __tablename__ = "limite_email"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    accion = Column(String(50), nullable=False)
    conteo = Column(Integer, nullable=False)
    inicio_ventana = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("email", "accion", name="uq_limite_email_email_accion"),
        CheckConstraint("conteo BETWEEN 1 AND 100", name="ck_limite_email_conteo_valido"),
    )

class Token(Base): # tabla para guardar los tokens para reseteo de contraseña vía email
    __tablename__ = "token_password"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_token_expira_despues"),
    )

class OTPCode(Base): # tabla para guardar los códigos otp para reseteo de contraseña vía celular
    __tablename__ = "otp_code"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=True)

    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="ck_otp_expira_despues"),
    )

class Blacklist(Base):
    __tablename__ = "blacklist_token"

    id = Column(Integer, primary_key=True)
    jti = Column(String(128), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=False)

class Estado_Turno(Base):
    __tablename__ = "estado_turno" # Esta tabla ya viene con estados puestos

    id = Column(Integer, primary_key=True)
    estado = Column(String(50), unique=True, nullable=False)

class Rol(Base):
    __tablename__ = "rol" # Esta tabla ya viene con roles puestos

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    tipo = Column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("nombre", "tipo", name="uq_rol_nombre_tipo"),
    )