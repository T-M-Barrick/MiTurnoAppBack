import requests
from fastapi import APIRouter, Depends

from core.variables import GEOREF_URL

router = APIRouter(prefix="/georef", tags=["Geo"])

@router.get("/provincias")
def get_provincias():
    r = requests.get(f"{GEOREF_URL}/provincias")
    return r.json()["provincias"]

@router.get("/departamentos")
def get_departamentos(provincia: str):
    r = requests.get(f"{GEOREF_URL}/departamentos", params={"provincia": provincia, "max": 500})
    return r.json()["departamentos"]

@router.get("/localidades")
def get_localidades(provincia: str, municipio: str):
    r = requests.get(f"{GEOREF_URL}/localidades", params={"provincia": provincia, "municipio": municipio, "max": 500})
    return r.json()["localidades"]

@router.get("/coordenadas")
def get_coordenadas(provincia: str, municipio: str, localidad: str, calle: str, altura: str):
    direccion = f"{calle} {altura}"
    r = requests.get(f"{GEOREF_URL}/direcciones", params={"provincia": provincia, "municipio": municipio,
            "localidad": localidad, "direccion": direccion, "max": 5})
    data = r.json()
    if data["cantidad"] == 0:
        return None   
    return data["direcciones"][0]  # devuelve lat/long y datos normalizados

@router.get("/reverse")
def reverse_geocode(lat: float, lng: float):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "json", "lat": lat, "lon": lng, "addressdetails": 1}

    r = requests.get(url, params=params, headers={"User-Agent": "MiApp"})
    data = r.json()

    if "display_name" not in data:
        return None

    return {"domicilio": data["display_name"]}
