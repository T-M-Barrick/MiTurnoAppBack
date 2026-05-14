import unicodedata

from sqlalchemy import (
    Column, Integer, String,
    SmallInteger, ForeignKey,
    DateTime, Date, Time,
    Float, Numeric, Boolean,
    Index, UniqueConstraint, CheckConstraint,
    func, or_, and_, text, cast, Interval, event, select,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint

from core.database import Base

def normalizar_email(email: str | None) -> str | None:
    if email is None:
        return None

    local, domain = email.split('@')

    if domain.startswith(("gmail.com", "googlemail.com")):
        domain = "gmail.com"
        local = local.replace('.', '').split('+')[0]
    elif domain.startswith(("outlook.com", "hotmail.com", "icloud.com", "me.com", "proton.me")):
        local = local.split('+')[0]
    elif domain.startswith(("yahoo.com", "ymail.com")):
        local = local.split('-')[0].split('+')[0]
    else:
        local = local.split('+')[0]

    return f"{local}@{domain}"

def quitar_acentos(texto: str) -> str:
    if not texto:
        return texto

    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))

def generar_busqueda_texto_para_sucursal(target, connection) -> str:

    empresa_nombre = None
    empresa_rubro = None
    empresa_rubro2 = None

    if target.empresa_id:
        result = connection.execute(
            select(
                Empresa.nombre,
                Empresa.rubro,
                Empresa.rubro2,
            ).where(Empresa.id == target.empresa_id)
        ).first()

        if result:
            empresa_nombre, empresa_rubro, empresa_rubro2 = result

    texto = " ".join(filter(None, [
        target.nombre,
        empresa_nombre,
        empresa_rubro,
        empresa_rubro2,
    ])).lower()

    return quitar_acentos(texto)

def generar_busqueda_texto_para_cliente(target) -> str:
    texto = " ".join(filter(None, [
        target.dni,
        target.apellido,
        target.nombre,
        target.email,
        target.telefono,
        target.telefono2,
        target.observacion,
    ])).lower()

    return quitar_acentos(texto)

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True) # Al ser PK simple con Integer, SQLAlchemy sobreentiende que autoincrement=True y no es necesario ponerlo
    dni = Column(String(8), nullable=False)
    apellido = Column(String(30), nullable=False) # nullable=False es NOT NULL
    nombre = Column(String(30), nullable=False)
    email = Column(String(255), nullable=False)
    email_normalizado = Column(String(255), unique=True, nullable=False)
    email_verificado = Column(Boolean, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    recordatorio_minutos_antes = Column(SmallInteger, nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=True)

    @validates("email")
    def guardar_email_normalizado(self, key, value):
        self.email_normalizado = normalizar_email(value)
        return value

    __table_args__ = (
        CheckConstraint("dni ~ '^[0-9]{6,8}$'", name="ck_usuario_dni_6_a_8_digitos"),
        CheckConstraint("recordatorio_minutos_antes >= 0", name="ck_usuario_recordatorio_por_defecto"),
    )

    # Relationships
    telefonos = relationship("Telefono", back_populates="usuario", passive_deletes=True) # Relación bidireccional gracias a back_populates
    direcciones = relationship("Direccion", back_populates="usuario", passive_deletes=True) # Relación bidireccional de uno a muchos con la tabla Direccion
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
    nombre = Column(String(40), nullable=False)
    email = Column(String(255), nullable=False)
    email_normalizado = Column(String(255), unique=True, nullable=False)
    email_verificado = Column(Boolean, nullable=False)
    rubro = Column(String(50), nullable=True)
    rubro2 = Column(String(50), nullable=True)
    logo_url = Column(String(255), nullable=True)
    logo_public_id = Column(String(50), nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=True)

    @validates("email")
    def guardar_email_normalizado(self, key, value):
        self.email_normalizado = normalizar_email(value)
        return value

    __table_args__ = (
        CheckConstraint("cuit ~ '^[0-9]{11}$'", name="ck_empresa_cuit_11_digitos"),
    )

    # Relationships
    sucursales = relationship("Sucursal", back_populates="empresa")
    miembros = relationship("Miembro_Empresa", back_populates="empresa")
    notificaciones = relationship("Notificacion", back_populates="empresa")

class Sucursal(Base):
    __tablename__ = "sucursal"

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    nombre = Column(String(40), nullable=True)
    email = Column(String(255), nullable=True)
    email_normalizado = Column(String(255), unique=True, nullable=True)
    email_verificado = Column(Boolean, nullable=True)
    busqueda_texto = Column(String, nullable=True)
    reserva_publica_habilitada = Column(Boolean, nullable=False)
    calificacion = Column(Numeric(4, 2), nullable=True)
    activa = Column(Boolean, nullable=False)

    @validates("email")
    def guardar_email_normalizado(self, key, value):
        self.email_normalizado = normalizar_email(value)
        return value

    __table_args__ = (
        UniqueConstraint(empresa_id, nombre, name="uq_sucursal_empresa_nombre", postgresql_nulls_not_distinct=True),
        Index(
            "ix_sucursal_busqueda_texto_trigram",
            text("busqueda_texto gin_trgm_ops"),
            postgresql_using="gin",
            postgresql_where=text(
                "activa = true AND reserva_publica_habilitada = true"
            ),
        ),
        CheckConstraint("calificacion BETWEEN 0 AND 10", name="ck_sucursal_calificacion_0_10"),
    )

    # Relationships
    empresa = relationship("Empresa", back_populates="sucursales")
    clientes = relationship("Cliente", back_populates="sucursal")
    telefonos = relationship("Telefono", back_populates="sucursal", passive_deletes=True)
    direccion = relationship("Direccion", back_populates="sucursal", uselist=False, passive_deletes=True)
    servicios_base = relationship("ServicioBase", back_populates="sucursal")
    miembros = relationship("Miembro_Sucursal", back_populates="sucursal")
    bloqueos = relationship("BloqueoSucursal", back_populates="sucursal")
    notificaciones = relationship("Notificacion", back_populates="sucursal")

@event.listens_for(Sucursal, "before_insert")
def before_insert_sucursal(mapper, connection, target):
    target.busqueda_texto = generar_busqueda_texto_para_sucursal(target, connection)


@event.listens_for(Sucursal, "before_update")
def before_update_sucursal(mapper, connection, target):
    target.busqueda_texto = generar_busqueda_texto_para_sucursal(target, connection)

class Cliente(Base):
    __tablename__ = "cliente_sucursal"

    id = Column(Integer, primary_key=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    dni = Column(String(8), nullable=False)
    apellido = Column(String(30), nullable=False)
    nombre = Column(String(30), nullable=False)
    email = Column(String(255), nullable=False)
    email_normalizado = Column(String(255), nullable=False)
    telefono = Column(String(30), nullable=True)
    telefono2 = Column(String(30), nullable=True)
    observacion = Column(String(500), nullable=True)
    busqueda_texto = Column(String, nullable=True)
    fecha_hora_alta = Column(DateTime, nullable=False)
    activo = Column(Boolean, nullable=False)

    @validates("email")
    def guardar_email_normalizado(self, key, value):
        self.email_normalizado = normalizar_email(value)
        return value

    __table_args__ = (
        Index("ix_cliente_sucursal_activo_id", sucursal_id, activo, id),
        # Índice trigram para búsqueda más rápida con %{search}%
        Index(
            "ix_cliente_busqueda_texto_trigram",
            text("busqueda_texto gin_trgm_ops"),
            postgresql_using="gin",
        ),
        UniqueConstraint(sucursal_id, email_normalizado, name="uq_cliente_sucursal_sucursal_id_email_normalizado"),
        CheckConstraint("dni ~ '^[0-9]{6,8}$'", name="ck_cliente_sucursal_dni_6_a_8_digitos"),
        CheckConstraint("length(telefono) >= 7", name="ck_cliente_sucursal_telefono_len"),
        CheckConstraint("length(telefono2) >= 7", name="ck_cliente_sucursal_telefono2_len"),
    )

    # Relationships
    sucursal = relationship("Sucursal", back_populates="clientes")
    bloqueo = relationship("BloqueoSucursal", back_populates="cliente", uselist=False)

@event.listens_for(Cliente, "before_insert")
def before_insert_cliente(mapper, connection, target):
    target.busqueda_texto = generar_busqueda_texto_para_cliente(target)


@event.listens_for(Cliente, "before_update")
def before_update_cliente(mapper, connection, target):
    target.busqueda_texto = generar_busqueda_texto_para_cliente(target)

class Telefono(Base):
    __tablename__ = "telefono"

    id = Column(Integer, primary_key=True)
    numero = Column(String(30), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True, index=True) # Relación muchos a uno con la tabla usuario (un usuario puede tener varios teléfonos)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=True, index=True) # Relación muchos a uno con la tabla sucursal (una sucursal puede tener varios teléfonos)

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
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), nullable=True, index=True) # NULL si pertenece a una sucursal
    sucursal_id = Column(Integer, ForeignKey("sucursal.id", ondelete="CASCADE"), nullable=True, index=True) # NULL si pertenece a un usuario
    calle = Column(String(255), nullable=True)
    altura = Column(String(255), nullable=True)
    localidad = Column(String(255), nullable=True)
    departamento = Column(String(255), nullable=True)
    provincia = Column(String(255), nullable=True)
    pais = Column(String(255), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    aclaracion = Column(String(255), nullable=True)

    @validates("lat", "lng")
    def normalizar_coordenada(self, key, value):
        return round(float(value), 6)

    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_lat_range"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="ck_lng_range"),
        CheckConstraint(
            "(usuario_id IS NOT NULL AND sucursal_id IS NULL) OR "
            "(usuario_id IS NULL AND sucursal_id IS NOT NULL)",
            name="ck_direccion_usuario_xor_sucursal"
        ),
    )

    # Relationships
    # En Direccion
    usuario = relationship("Usuario", back_populates="direcciones")
    sucursal = relationship("Sucursal", back_populates="direccion")

class Turno(Base):
    __tablename__ = "turno"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("cliente_sucursal.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    servicio_id = Column(Integer, nullable=False) # apunta a la tabla Servicio
    nombre_de_servicio = Column(String(50), nullable=False)
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
        Index("ix_turno_usuario_eliminado_fecha_hora", usuario_id, eliminado_por_usuario, fecha_hora),
        Index("ix_turno_sucursal_eliminado_fecha_hora", sucursal_id, eliminado_por_sucursal, fecha_hora),
        Index("ix_turno_servicio_estado_turno_fecha_hora", servicio_id, estado_turno_sucursal_id, fecha_hora),
        Index("ix_turno_profesional_estado_turno", profesional_id, estado_turno_sucursal_id),
        Index("ix_turno_enviar_recordatorios", recordatorio_enviado, estado_turno_usuario_id, recordatorio_fecha_hora),
        Index(
            "ix_turno_limpieza", fecha_hora, postgresql_where=or_(eliminado_por_usuario == False, eliminado_por_sucursal == False)
        ),
        UniqueConstraint(usuario_id, servicio_id, fecha_hora, name="uq_turno_usuario_servicio_fecha"),
        UniqueConstraint(cliente_id, servicio_id, fecha_hora, name="uq_turno_cliente_servicio_fecha"),
        CheckConstraint("servicio_id >= 1", name="ck_turno_servicio_id_pos"),
        CheckConstraint("duracion > 0", name="ck_turno_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_turno_precio_pos"),
        ExcludeConstraint(
            (
                func.tstzrange(
                    fecha_hora,
                    fecha_hora + cast(func.concat(duracion, ' minutes'), Interval()),
                    '[)',
                ),
                "&&"
            ),
            (
                usuario_id,
                "="
            ),
            name="no_overlap_turnos_usuario",
            using="gist",
            where=and_(
                usuario_id.isnot(None),
                eliminado_por_usuario == False,
                estado_turno_usuario_id == 1,
            ),
        ),
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
    nombre = Column(String(50), nullable=False)
    aclaracion = Column(String(255), nullable=True) # cualquier aclaración o descripción
    profesional_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)
    minutos_minimos_anticipacion_reserva = Column(Integer, nullable=False)
    limite_dias_reserva = Column(Integer, nullable=True) # contando el día actual e incluyendo al día puesto como el último
    # Si este atributo es True, significa que solo puede cancelar los turnos de un profesional el mismo profesional o un superior suyo
    cancelacion_turno_limitada = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            sucursal_id,
            nombre,
            profesional_id,
            name="uq_servicio_sucursal_nombre_profesional",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("minutos_minimos_anticipacion_reserva >= 0", name="ck_servicio_minutos_minimos_anticipacion_reserva"),
        CheckConstraint(
            "limite_dias_reserva >= 0", name="ck_servicio_limite_dias_reserva"
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
        Index("ix_servicio_servicio_base_id", servicio_base_id),
        CheckConstraint("duracion > 0", name="ck_servicio_duracion_pos"),
        CheckConstraint("precio >= 0", name="ck_servicio_precio_pos"),
        CheckConstraint(
            "vigente_hasta IS NULL OR vigente_desde <= vigente_hasta", name="ck_servicio_fecha_franja_valida"
        ),
        # Constraint para que los intervalos de fechas de servicios de un mismo servicio_base no se superpongan ni un día
        ExcludeConstraint(
            ("servicio_base_id", "="),
            (
                func.daterange(
                    vigente_desde,
                    func.coalesce(vigente_hasta, text("'infinity'")),
                    "[]", # rango cerrado, ni un día puede coincidir
                ),
                "&&",
            ),
            name="ex_servicio_rangos_de_vigencia_no_superpuestos",
            using="gist",
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
        Index("ix_disponibilidad_servicio_id", servicio_id),
        CheckConstraint("dia BETWEEN 0 AND 6", name="ck_disponibilidad_dia_semana_0_6"),
        CheckConstraint("hora_inicio <= hora_fin", name="ck_disponibilidad_horario_valido"),
        CheckConstraint(
            "intervalo > 0", name="ck_disponibilidad_intervalo_pos"
        ), # si la dejo ser 0, después puede surgir problema cuando divida algo por este atributo intervalo
        CheckConstraint(
            "cant_turnos_max >= 0", name="ck_disponibilidad_cant_turnos_max_pos"
        ), # puede ser 0 ya que quizás el admin quiso sacar temporalmente la disponibilidad para ese día en el servicio

        # Constraint para que los bloques horarios de disponibilidades de un mismo servicio y día no se superpongan ni un minuto
        ExcludeConstraint(
            ("servicio_id", "="),
            ("dia", "="),
            (
                text(
                    "tsrange('epoch'::date + hora_inicio, 'epoch'::date + hora_fin, '[]')"
                ), # [] es rango cerrado, ni un minuto puede coincidir
                "&&", # operador "solapamiento"
            ),
            name="ex_disponibilidad_rangos_horarios_no_superpuestos",
            using="gist",
        ),
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
        Index("ix_excepcion_servicio_base_id", servicio_base_id),
        CheckConstraint("fecha_inicio <= fecha_fin", name="ck_excepcion_fecha_franja_valida"),
        # Constraint para que los intervalos de fechas de excepciones (bloqueos) de un mismo servicio_base no se superpongan ni un día
        ExcludeConstraint(
            ("servicio_base_id", "="),
            (
                func.daterange(
                    fecha_inicio,
                    fecha_fin,
                    "[]", # rango cerrado, ni un día puede coincidir
                ),
                "&&",
            ),
            name="ex_excepcion_fecha_servicio_rangos_de_fechas_no_superpuestos",
            using="gist",
        ),
    )

    servicio_base = relationship("ServicioBase", back_populates="excepciones_fechas")

class Miembro_Empresa(Base):
    __tablename__ = "miembro_empresa"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    empresa_id = Column(Integer, ForeignKey("empresa.id"), nullable=False, index=True)
    rol_id = Column(SmallInteger, ForeignKey("rol.id"), nullable=False) # 1: 'PROPIETARIO' o 2: 'GERENTE_EMPRESA'

    __table_args__ = (
        UniqueConstraint(usuario_id, empresa_id, name="uq_m_e_usuario_empresa"),
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
        UniqueConstraint(usuario_id, sucursal_id, name="uq_m_s_usuario_sucursal"),
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
    cliente_id = Column(Integer, ForeignKey("cliente_sucursal.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("usuario.id"), nullable=False) # quién lo bloqueó
    motivo = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint(sucursal_id, cliente_id, name="uq_s_b_sucursal_cliente"),
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
    fecha_hora_minima_de_envio = Column(DateTime, nullable=False)
    leida = Column(Boolean, nullable=False)

    __table_args__ = (
        Index(
            "ix_notificacion_usuario",
            usuario_id,
            fecha_hora_minima_de_envio,
            id.desc(),
            postgresql_where=text("empresa_id IS NULL AND sucursal_id IS NULL")
        ),
        Index(
            "ix_notificacion_empresa",
            usuario_id,
            empresa_id,
            fecha_hora_minima_de_envio,
            id.desc(),
            postgresql_where=text("empresa_id IS NOT NULL")
        ),
        Index(
            "ix_notificacion_sucursal",
            usuario_id,
            sucursal_id,
            fecha_hora_minima_de_envio,
            id.desc(),
            postgresql_where=text("sucursal_id IS NOT NULL")
        ),
        Index("ix_notificacion_limpieza", leida, created_at),
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
    email_normalizado = Column(String(255), nullable=False)
    accion = Column(String(50), nullable=False)
    conteo = Column(Integer, nullable=False)
    inicio_ventana = Column(DateTime, nullable=False)
    
    @validates("email_normalizado")
    def guardar_email_normalizado(self, key, value):
        return normalizar_email(value)

    __table_args__ = (
        UniqueConstraint(email_normalizado, accion, name="uq_limite_email_email_normalizado_accion"),
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

    __table_args__ = (
        Index("ix_blacklist_limpieza", expires_at),
    )

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
        UniqueConstraint(nombre, tipo, name="uq_rol_nombre_tipo"),
    )