from datetime import datetime, timedelta
import math
import io

import requests
from PIL import Image

from core.constantes import DIAS_NOMBRES, MAX_LOGO_SIZE, Rol
from core import exceptions

def mapear_nombre_dia_semana(dia: int):

    dia_nombre = DIAS_NOMBRES[dia]

    return dia_nombre

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

    params = {"q": direccion, "format": "json", "limit": 1}

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

# las coordenadas1 son las de la casa del usuario y las coordenadas2 son de la empresa que se está analizando
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

def rol_superior(rol1: Rol, rol2: Rol):
    return rol1.value < rol2.value

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