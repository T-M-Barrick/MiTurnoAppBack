import requests
from fastapi import APIRouter, Depends

from core.variables import GEOREF_URL

router = APIRouter(prefix="/georef", tags=["Geo"])

@router.get("/provincias")
def get_provincias():
    try:
        r = requests.get(f"{GEOREF_URL}/provincias", timeout=5)
        data = r.json()

        if "provincias" not in data:
            return {"error": "La API Georef no devolvió provincias", "detalle": data}

        return data["provincias"]

    except Exception as e:
        return {"error": "Falló la conexión con la API Georef", "detalle": str(e)}

@router.get("/departamentos")
def get_departamentos(provincia: str):
    try:
        r = requests.get(
            f"{GEOREF_URL}/departamentos",
            params={"provincia": provincia, "max": 500},
            timeout=5
        )
        data = r.json()

        if "departamentos" not in data:
            return {"error": "La API Georef no devolvió departamentos", "detalle": data}

        return data["departamentos"]

    except Exception as e:
        return {"error": "Falló la conexión con la API Georef", "detalle": str(e)}

@router.get("/localidades")
def get_localidades(provincia: str, municipio: str):
    try:
        r = requests.get(
            f"{GEOREF_URL}/localidades",
            params={"provincia": provincia, "municipio": municipio, "max": 500},
            timeout=5
        )
        data = r.json()

        if "localidades" not in data:
            return {"error": "La API Georef no devolvió localidades", "detalle": data}

        return data["localidades"]

    except Exception as e:
        return {"error": "Falló la conexión con la API Georef", "detalle": str(e)}

@router.get("/coordenadas")
def get_coordenadas(provincia: str, municipio: str, localidad: str, calle: str, altura: str):

    direccion = f"{calle} {altura}"

    try:
        r = requests.get(
            f"{GEOREF_URL}/direcciones",
            params={
                "provincia": provincia,
                "municipio": municipio,
                "localidad": localidad,
                "direccion": direccion,
                "max": 5
            },
            timeout=5
        )

        data = r.json()

        if "direcciones" not in data or data.get("cantidad", 0) == 0:
            return {"error": "La API Georef no encontró esa dirección", "detalle": data}

        return data["direcciones"][0]

    except Exception as e:
        return {"error": "Falló la conexión con la API Georef", "detalle": str(e)}

@router.get("/reverse")
def reverse_geocode(lat: float, lng: float):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "format": "json",
            "lat": lat,
            "lon": lng,
            "addressdetails": 1
        }

        r = requests.get(url, params=params, headers={"User-Agent": "MiApp"}, timeout=5)
        data = r.json()

        if "display_name" not in data:
            return {"error": "No se pudo obtener dirección desde OSM", "detalle": data}

        return {"domicilio": data["display_name"]}

    except Exception as e:
        return {"error": "Falló la conexión con OpenStreetMap", "detalle": str(e)}
