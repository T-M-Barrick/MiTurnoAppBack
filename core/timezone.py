from datetime import date, time, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from core import constantes, exceptions

# =========================
# CONFIGURACIÓN CENTRAL
# =========================

# Zona horaria de la sucursal (por ahora única)
SUCURSAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires") # representa el huso de todo Argentina

# UTC explícito
UTC = timezone.utc

# =========================
# FECHAS BASE
# =========================

def now_utc() -> datetime:
    """
    Devuelve el datetime actual en UTC (aware)
    """
    return datetime.now(UTC)

def is_utc(dt: datetime) -> bool:
    """
    Indica si un datetime es aware UTC
    """
    return dt.tzinfo is not None and dt.utcoffset() == timedelta(0)

def validate_aware_utc(dt: datetime) -> datetime: # función utilizada en validaciones pydantic de la carpeta schemas

    if dt.tzinfo is None:
        raise ValueError("El datetime debe ser timezone-aware y estar en UTC")

    if dt.utcoffset() != UTC.utcoffset(None):
        raise ValueError("El datetime debe estar en UTC")

    return dt

# =========================
# CONVERSIONES
# =========================

def ensure_utc(dt: datetime) -> datetime:
    """
    Garantiza que un datetime sea UTC aware:
    - Si entra naive, lo convierte a aware UTC sin cambiarle la hora, solo poniéndole la etiqueta UTC.
    - Si entra aware horario local (no UTC), lo convierte a aware UTC cambiando la hora para que dé justo.
    - Si entra aware UTC, no hace nada.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)

def utc_to_local(dt_utc: datetime) -> datetime:
    """
    Devuelve un datetime aware en la zona horaria local de la sucursal:
    - Si entra naive, lo asume en UTC y luego lo convierte a aware horario local cambiándole la hora.
    - Si entra aware horario local, lanza error.
    - Si entra aware UTC, lo convierte a aware horario local cambiándole la hora.
    """
    if dt_utc.tzinfo is not None and dt_utc.utcoffset() != UTC.utcoffset(None):
        raise exceptions.TimezoneInvalidError() # utc_to_local no acepta datetime aware no UTC
    dt_utc = ensure_utc(dt_utc)
    return dt_utc.astimezone(SUCURSAL_TZ)

def local_to_utc(dt_local: datetime) -> datetime:
    """
    Devuelve un datetime aware UTC:
    - Si entra naive, lo asume en horario local y luego lo convierte a aware UTC cambiándole la hora.
    - Si entra aware horario local, lo convierte a aware UTC cambiándole la hora.
    - Si entra aware UTC, lanza error.
    """
    if dt_local.tzinfo is not None and dt_local.utcoffset() == UTC.utcoffset(None):
        raise exceptions.TimezoneInvalidError() # local_to_utc no acepta datetime aware UTC
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=SUCURSAL_TZ)
    return dt_local.astimezone(UTC)

def to_naive_utc(dt_utc: datetime) -> datetime:
    """
    Devuelve un datetime naive UTC:
    - Si entra naive, no hace nada.
    - Si entra aware horario local, lo convierte a naive UTC cambiándole la hora.
    - Si entra aware UTC, lo convierte a naive UTC sin cambiarle la hora, solo sacándole la etiqueta UTC.

    USAR SIEMPRE antes de guardar en PostgreSQL
    """
    dt_utc = ensure_utc(dt_utc)
    return dt_utc.replace(tzinfo=None)

# =========================
# FUNCIONES DE NEGOCIO
# =========================

def extraer_dia_y_hora_en_local(fecha_hora_utc: datetime) -> tuple[int, time]:
    """
    A partir de un datetime UTC devuelve:
    - día de la semana (0=lunes, 6=domingo).
    - hora local (time).
    """

    fecha_hora_local = utc_to_local(fecha_hora_utc)

    dia_semana = fecha_hora_local.weekday() # 0 = lunes, 6 = domingo
    hora = fecha_hora_local.time() # hora del turno
    
    return dia_semana, hora

def validar_turno_horario(fecha_hora_turno_utc: datetime, minutos_minimos: int):
    """
    Valida que el turno sea al menos 'minutos_minimos' en el futuro
    """
    fecha_hora_turno_utc = ensure_utc(fecha_hora_turno_utc) # garantía defensiva
    ahora = now_utc()
    limite = ahora + timedelta(minutes=minutos_minimos)

    # No cumple anticipación mínima
    if fecha_hora_turno_utc < limite:
        return False

def validar_turno_dias_max(fecha_hora_turno_utc: datetime, dias_max: int):
    '''
    Valida límite máximo de días para sacar turno
    '''
    fecha_hora_turno_utc = ensure_utc(fecha_hora_turno_utc) # garantía defensiva
    hoy = now_utc() # datetime aware UTC
    max_fecha = (hoy + timedelta(days=dias_max - 1)).date() # Restamos 1 porque hoy cuenta como día 1

    if fecha_hora_turno_utc.date() > max_fecha:
        return False
