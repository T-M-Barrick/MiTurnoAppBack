import requests
from fastapi import APIRouter, Depends

from core.auxiliares import buscar_localidad, buscar_direccion_completa
from core.variables import GEOREF_URL, NOMINATIM_URL

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
def get_coordenadas(
    provincia: str,
    municipio: str,
    localidad: str,
    calle: str | None = None,
    altura: str | None = None
):
    # Si llega calle + altura → buscar dirección exacta
    if calle and altura:
        return buscar_direccion_completa(
            provincia=provincia,
            municipio=municipio,
            localidad=localidad,
            calle=calle,
            altura=altura,
            url=NOMINATIM_URL
        )

    # Caso contrario → buscar solo localidad
    return buscar_localidad(
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        url=NOMINATIM_URL
    )
