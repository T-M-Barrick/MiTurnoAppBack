import requests
from fastapi import APIRouter, Depends

from core.variables import GEOREF_URL

router = APIRouter(prefix="/georef", tags=["Geo"])

@router.get("/provincias")
def get_provincias():
    r = requests.get(f"{GEOREF_URL}/provincias")
    return r.json()["provincias"]

@router.get("/departamentos/{provincia}")
def get_departamentos(provincia: str):
    r = requests.get(f"{GEOREF_URL}/departamentos", params={"provincia": provincia, "max": 500})
    return r.json()["departamentos"]

@router.get("/localidades")
def get_localidades(provincia: str, municipio: str):
    r = requests.get(f"{GEOREF_URL}/localidades", params={"provincia": provincia, "municipio": municipio, "max": 500})
    return r.json()["localidades"]

@router.get("/coordenadas")
def get_coordenadas(calle: str, altura: str, provincia: str):
    direccion = f"{calle} {altura}"
    r = requests.get(f"{GEOREF_URL}/direcciones", params={"direccion": direccion, "provincia": provincia})
    data = r.json()
    if data["cantidad"] == 0:
        return None
    return data["direcciones"][0]  # devuelve lat/long
