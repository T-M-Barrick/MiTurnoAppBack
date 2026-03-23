from datetime import datetime, timedelta
import unicodedata
import math
import io

import requests
from PIL import Image
from sqlalchemy.orm import Session

from core.constantes import DIAS_NOMBRES, MAX_LOGO_SIZE
from core import exceptions, timezone

def mapear_nombre_dia_semana(dia: int):

    dia_nombre = DIAS_NOMBRES[dia]

    return dia_nombre

def nombre_empresa(empresa_nombre: str, sucursal_nombre: str | None):
    emp_nombre = empresa_nombre
    if sucursal_nombre:
        emp_nombre += f' - {sucursal_nombre}'
    return emp_nombre

def quitar_acentos(texto: str) -> str:
    if not texto:
        return texto

    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))

def buscar_localidad(provincia: str, municipio: str, localidad: str, url: str):
    """
    Busca las coordenadas de una localidad usando Nominatim (OpenStreetMap).
    Devuelve lat y lng.
    """

    # Construir consulta completa
    query = f"{localidad}, {municipio}, {provincia}, Argentina"

    params = {"q": query, "format": "json", "limit": 1}

    try:
        r = requests.get(url, params=params, timeout=5, headers={"User-Agent": "MiApp/1.0"})
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise exceptions.GeoRefUnavailableError() from e

    try:
        resultados = r.json()
    except ValueError as e:
        raise exceptions.GeoRefInvalidResponseError() from e

    if not resultados:
        raise exceptions.GeoRefLocalidadNotFoundError()

    loc = resultados[0]
    lat = loc.get("lat")
    lon = loc.get("lon")

    if not lat or not lon:
        raise exceptions.GeoRefInvalidResponseError() # la localidad no tiene coordenadas

    return {"lat": lat, "lng": lon}

def buscar_direccion_completa(provincia: str, municipio: str, localidad: str, calle: str, altura: str, url: str):
    """
    Busca coordenadas y dirección completa usando la URL que le pases.
    Si la URL es de Nominatim, hace forward geocoding (calle + altura → lat/lon).
    """

    # Construir la dirección completa
    direccion_completa = f"{calle} {altura}, {localidad}, {municipio}, {provincia}, Argentina"

    params = {"q": direccion_completa, "format": "json", "limit": 1}

    try:
        r = requests.get(url, params=params, timeout=5, headers={"User-Agent": "MiApp/1.0"})
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise exceptions.GeoRefUnavailableError() from e

    try:
        resultados = r.json()
    except ValueError as e:
        raise exceptions.GeoRefInvalidResponseError() from e

    if not resultados:
        raise exceptions.GeoRefDireccionNotFoundError()

    d = resultados[0]

    lat = d.get("lat")
    lon = d.get("lon")

    if not lat or not lon:
        raise exceptions.GeoRefInvalidResponseError() # la dirección no tiene coordenadas
    
    calle_nominatim = ""
    address = d.get("address", {})
    if address:
        # Intentar varios campos posibles donde Nominatim podría poner la calle
        calle_nominatim = address.get("road") or address.get("pedestrian") or address.get("footway") \
                        or address.get("residential") or address.get("path") or ""
    else:
        # fallback: extraer de display_name
        display_name = d.get("display_name", "")
        partes = display_name.split(",")
        if len(partes) >= 2:
            calle_nominatim = partes[1].strip()

    return {"lat": lat, "lng": lon, "calle": calle_nominatim}

# las coordenadas1 son las de la casa del usuario y las coordenadas2 son de la sucursal que se está analizando
def distancia_km(lat1, lng1, lat2, lng2):
    R = 6371 # radio terrestre en km que sirve para la fórmula Haversine
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlng/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_rol_id(db: Session, nombre: str, tipo: str) -> int:

    rol = (
        db.query(models.Rol)
        .filter_by(nombre=nombre, tipo=tipo)
        .first()
    )

    if not rol:
        raise ValueError(f"Rol inexistente: {nombre} para tipo {tipo}")

    return rol.id

def rol_superior(rol1: str, rol2: str) -> bool:

    JERARQUIA = {
        "PROPIETARIO": 100,
        "GERENTE_EMPRESA": 80,
        "GERENTE_SUCURSAL": 40,
        "EMPLEADO": 20,
    }

    try:
        return JERARQUIA[rol1] > JERARQUIA[rol2]
    except KeyError as e:
        raise ValueError(f"Rol inválido: {e.args[0]}")

def validar_logo(logo_bytes: bytes):

    if len(logo_bytes) > MAX_LOGO_SIZE:
        maximo = MAX_LOGO_SIZE // 1024
        raise exceptions.LogoTooLargeError(field="logo", max_kb=maximo)

    try:
        with Image.open(io.BytesIO(logo_bytes)) as img:
            if img.format not in ["PNG", "JPEG", "WEBP"]: # como formato no existe JPG, sino que es JPEG
                raise exceptions.LogoInvalidFormatError(
                    field="logo",
                    allowed=["PNG", "JPG", "WEBP"] # le devuelvo al usuario JPG para que entienda
                )
    except Exception:
        raise exceptions.LogoInvalidError(field="logo")

def formatear_fecha_hora_turno(fecha_hora_turno_aware_utc: datetime) -> str:

    # Garantía defensiva (por si alguien se equivoca)
    fecha_hora_turno_aware_utc = timezone.ensure_utc(fecha_hora_turno_aware_utc)

    ahora_aware_utc = timezone.now_utc() # aware UTC

    # Convertimos una sola vez a local
    fecha_hora_turno_aware_local = timezone.utc_to_local(fecha_hora_turno_aware_utc) # lo convierte a aware horario local cambiándole la hora
    ahora_aware_local = timezone.utc_to_local(ahora_aware_utc) # lo convierte a aware horario local cambiándole la hora

    dia_local = fecha_hora_turno_aware_local.weekday() # devuelve 0, 1, 2, ..., 6
    nombre_dia = mapear_nombre_dia_semana(dia_local) # le ponemos nombre a dia_local

    fecha_local_str = fecha_hora_turno_aware_local.strftime("%d/%m") # pasamos al formato correspondiente en string
    hora_local_str = fecha_hora_turno_aware_local.strftime("%H:%M") # pasamos al formato correspondiente en string

    # MISMO DÍA (en horario local)
    if fecha_hora_turno_aware_local.date() == ahora_aware_local.date():
        return f"hoy {nombre_dia} {fecha_local_str} a las {hora_local_str} hs"

    # MAÑANA (en horario local)
    if fecha_hora_turno_aware_local.date() == ahora_aware_local.date() + timedelta(days=1):
        return f"mañana {nombre_dia} {fecha_local_str} a las {hora_local_str} hs"

    # OTRO DÍA
    return f"el día {nombre_dia} {fecha_local_str} a las {hora_local_str} hs"