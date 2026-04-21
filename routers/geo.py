import requests
from fastapi import APIRouter, Query

from core import exceptions
from core.constantes import GEOREF_URL, NOMINATIM_URL
from core.auxiliares import buscar_localidad, buscar_direccion_completa

router = APIRouter(prefix="/georef", tags=["Geo"])

@router.get("/provincias", status_code=200)
def obtener_provincias() -> list[dict]:

    try:
        r = requests.get(f"{GEOREF_URL}/provincias", timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException:
        raise exceptions.GeoRefUnavailableError()

    try:
        resultados = r.json()
    except ValueError as e:
        raise exceptions.GeoRefInvalidResponseError() from e

    if "provincias" not in resultados:
        raise exceptions.GeoRefInvalidResponseError()

    provincias = resultados["provincias"]
    provincias.sort(key=lambda x: x["nombre"])

    return provincias

@router.get("/departamentos", status_code=200)
def obtener_departamentos(
    provincia: str = Query(..., min_length=1, max_length=255),
) -> list[dict]:

    try:
        r = requests.get(f"{GEOREF_URL}/departamentos", params={"provincia": provincia, "max": 500}, timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException:
        raise exceptions.GeoRefUnavailableError()

    try:
        resultados = r.json()
    except ValueError as e:
        raise exceptions.GeoRefInvalidResponseError() from e

    if "departamentos" not in resultados:
        raise exceptions.GeoRefInvalidResponseError()

    departamentos = resultados["departamentos"]
    departamentos.sort(key=lambda x: x["nombre"])

    return departamentos

@router.get("/localidades", status_code=200)
def obtener_localidades(
    provincia: str = Query(..., min_length=1, max_length=255),
    municipio: str = Query(..., min_length=1, max_length=255),
) -> list[dict]:

    try:
        r = requests.get(f"{GEOREF_URL}/localidades", params={"provincia": provincia, "municipio": municipio, "max": 500}, timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException:
        raise exceptions.GeoRefUnavailableError()

    try:
        resultados = r.json()
    except ValueError as e:
        raise exceptions.GeoRefInvalidResponseError() from e

    if "localidades" not in resultados:
        raise exceptions.GeoRefInvalidResponseError()

    localidades = resultados["localidades"]
    localidades.sort(key=lambda x: x["nombre"])

    return localidades

@router.get("/coordenadas", status_code=200)
def obtener_coordenadas(
    provincia: str = Query(..., min_length=1, max_length=255),
    municipio: str = Query(..., min_length=1, max_length=255),
    localidad: str = Query(..., min_length=1, max_length=255),
    calle: str | None = Query(default=None, min_length=1, max_length=255),
    altura: str | None = Query(default=None, min_length=1, max_length=255),
) -> dict:

    if calle and altura:
        # Si llega calle + altura → buscar dirección exacta
        direccion_completa = buscar_direccion_completa(provincia=provincia, 
            municipio=municipio, localidad=localidad, calle=calle, altura=altura, url=NOMINATIM_URL)
        return direccion_completa
    
        # Caso contrario → buscar solo localidad
    loc = buscar_localidad(provincia=provincia, municipio=municipio, localidad=localidad, url=NOMINATIM_URL)
    return loc