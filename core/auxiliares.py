from datetime import datetime, timedelta
import math
import base64
import io

import requests
from PIL import Image

from core import schemas
from core.variables import DIAS_NOMBRES, MAX_LOGO_SIZE

# Convierte un objeto de la clase Usuario de SQLAlchemy en uno de clase UsuarioLoginOut o UsuarioUpdateOut de Pydantic (y agrega turnos si tiene)
def convertir_orm_pydantic_usuario(user, update=False, turnos_del_usuario=[]):

    if not update:
        us = schemas.UserLoginOut(
            id=user.id,
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,

            telefonos=[[t.id, t.numero] for t in user.telefonos],

            direcciones=[schemas.DireccionOut(
                id=d.id,
                calle=d.calle,
                altura=d.altura,
                localidad=d.localidad,
                departamento=d.departamento,
                provincia=d.provincia,
                pais=d.pais,
                lat=d.lat,
                lng=d.lng,
                aclaracion=d.aclaracion) for d in user.direcciones],
            
            favoritos=[schemas.EmpresaOut(
                id=e.id,
                cuit=e.cuit,
                nombre=e.nombre,
                email=e.email,
                rubro=e.rubro,
                rubro2=e.rubro2,
                calificacion=e.calificacion,
                telefonos=[t.numero for t in e.telefonos],
                direccion=schemas.DireccionOut(
                    id=e.direccion.id,
                    calle=e.direccion.calle,
                    altura=e.direccion.altura,
                    localidad=e.direccion.localidad,
                    departamento=e.direccion.departamento,
                    provincia=e.direccion.provincia,
                    pais=e.direccion.pais,
                    lat=e.direccion.lat,
                    lng=e.direccion.lng,
                    aclaracion=e.direccion.aclaracion),
                logo=codificar_logo(e.logo)
            ) for e in user.favoritos],

            turnos=[schemas.TurnoOut(
                id=turn.id,
                empresa_id=turn.empresa_id,
                empresa=turn.empresa.nombre,
                logo_empresa=codificar_logo(turn.empresa.logo),
                direccion=schemas.DireccionOut(
                    id=turn.empresa.direccion.id,
                    calle=turn.empresa.direccion.calle,
                    altura=turn.empresa.direccion.altura,
                    localidad=turn.empresa.direccion.localidad,
                    departamento=turn.empresa.direccion.departamento,
                    provincia=turn.empresa.direccion.provincia,
                    pais=turn.empresa.direccion.pais,
                    lat=turn.empresa.direccion.lat,
                    lng=turn.empresa.direccion.lng,
                    aclaracion=turn.empresa.direccion.aclaracion),
                fecha_hora=turn.fecha_hora,
                nombre_de_servicio=turn.nombre_de_servicio,
                duracion=turn.duracion,
                precio=turn.precio,
                aclaracion_de_servicio=turn.aclaracion_de_servicio,
                profesional_dni=turn.profesional.dni if turn.profesional else None,
                profesional_apellido=turn.profesional.apellido if turn.profesional else None,
                profesional_nombre=turn.profesional.nombre if turn.profesional else None,
                estado_turno=turn.estado_turno_usuario.estado,
                recordatorio=turn.recordatorio.minutos_antes if turn.recordatorio else None
            ) for turn in turnos_del_usuario]
        )   
    if update:
        us = schemas.UserUpdateOut(
            id=user.id,
            dni=user.dni,
            apellido=user.apellido,
            nombre=user.nombre,
            email=user.email,

            telefonos=[[t.id, t.numero] for t in user.telefonos],

            direcciones=[schemas.DireccionOut(
                id=d.id,
                calle=d.calle,
                altura=d.altura,
                localidad=d.localidad,
                departamento=d.departamento,
                provincia=d.provincia,
                pais=d.pais,
                lat=d.lat,
                lng=d.lng,
                aclaracion=d.aclaracion) for d in user.direcciones],
            
            favoritos=[schemas.EmpresaOut(
                id=e.id,
                cuit=e.cuit,
                nombre=e.nombre,
                email=e.email,
                rubro=e.rubro,
                rubro2=e.rubro2,
                calificacion=e.calificacion,
                telefonos=[t.numero for t in e.telefonos],
                direccion=schemas.DireccionOut(
                    id=e.direccion.id,
                    calle=e.direccion.calle,
                    altura=e.direccion.altura,
                    localidad=e.direccion.localidad,
                    departamento=e.direccion.departamento,
                    provincia=e.direccion.provincia,
                    pais=e.direccion.pais,
                    lat=e.direccion.lat,
                    lng=e.direccion.lng,
                    aclaracion=e.direccion.aclaracion),
                logo=codificar_logo(e.logo)
            ) for e in user.favoritos]
        )
        
    return us # us será un objeto de clase UsuarioLoginOut o de la clase UsuarioUpdateOut de Pydantic

# Convierte un objeto de la clase Empresa de SQLAlchemy en uno de clase EmpresaPanelOut de Pydantic
def convertir_orm_pydantic_empresa(empresa, miembro_rol):

    # Armar listas anidadas según schemas
    telefonos = [[t.id, t.numero] for t in empresa.telefonos]

    direccion_out = schemas.DireccionOut(
        id=empresa.direccion.id,
        calle=empresa.direccion.calle,
        altura=empresa.direccion.altura,
        localidad=empresa.direccion.localidad,
        departamento=empresa.direccion.departamento,
        provincia=empresa.direccion.provincia,
        pais=empresa.direccion.pais,
        lat=empresa.direccion.lat,
        lng=empresa.direccion.lng,
        aclaracion=empresa.direccion.aclaracion)
    
    servicios_out = []
    for s in empresa.servicios:
        profesional = s.profesional
        usuario = profesional.usuario if profesional else None

        servicios_out.append(
            schemas.ServicioOut(
                id=s.id,
                nombre=s.nombre,
                duracion=s.duracion,
                precio=s.precio,
                aclaracion=s.aclaracion,
                profesional_id=s.miembro_empresa_id,
                profesional_dni=usuario.dni if usuario else None,
                profesional_apellido=usuario.apellido if usuario else None,
                profesional_nombre=usuario.nombre if usuario else None,
                disponibilidades=[
                    schemas.DisponibilidadServicio(
                        dia=d.dia,
                        hora_inicio=d.hora_inicio,
                        hora_fin=d.hora_fin,
                        intervalo=d.intervalo,
                        cant_turnos_max=d.cant_turnos_max) for d in s.disponibilidades]
            )
        )

    turnos = crud.get_turnos(db, empresa_id, user=False)
    turnos_out = [schemas.TurnoEmpresaOut(
        id=t.id,
        usuario_dni=t.usuario.dni,
        usuario_apellido=t.usuario.apellido,
        usuario_nombre=t.usuario.nombre,
        fecha_hora=t.fecha_hora,
        servicio_id=t.servicio_id,
        nombre_de_servicio=t.nombre_de_servicio,
        duracion=t.duracion,
        precio=t.precio,
        aclaracion_de_servicio=t.aclaracion_de_servicio,
        profesional_dni=t.profesional.dni if t.profesional else None,
        profesional_apellido=t.profesional.apellido if t.profesional else None,
        profesional_nombre=t.profesional.nombre if t.profesional else None,
        estado_turno=t.estado_turno_empresa.estado) for t in turnos]

    miembros_out = [schemas.UserOut(
        id=m.usuario.id,
        dni=m.usuario.dni,
        apellido=m.usuario.apellido,
        nombre=m.usuario.nombre,
        email=m.usuario.email,
        rol=m.rol) for m in empresa.miembros]

    empresa_out = schemas.EmpresaPanelOut(
        id=empresa.id,
        cuit=empresa.cuit,
        nombre=empresa.nombre,
        email=empresa.email,
        rubro=empresa.rubro,
        rubro2=empresa.rubro2,
        calificacion=empresa.calificacion,
        telefonos=telefonos,
        direccion=direccion_out,
        logo=codificar_logo(empresa.logo),
        servicios=servicios_out,
        turnos=turnos_out,
        miembros=miembros_out,
        rol=miembro_rol)

    return empresa_out

def extraer_dia_y_hora(fecha_hora: datetime):
    """
    Convierte un datetime en día de la semana y hora
    """
    dias_nombres = DIAS_NOMBRES 
    dia_semana = fecha_hora.weekday() # 0 = lunes, 6 = domingo

    nombre_dia = dias_nombres[dia_semana]
    hora = fecha_hora.time() # hora del turno
    
    return nombre_dia, hora

def buscar_localidad(provincia: str, municipio: str, localidad: str, url: str):
    """
    Busca las coordenadas de una localidad usando Nominatim (OpenStreetMap).
    Devuelve lat y lng.
    """
    try:
        # Construir consulta completa
        query = f"{localidad}, {municipio}, {provincia}, Argentina"

        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }

        r = requests.get(url, params=params, timeout=5, headers={"User-Agent": "MiApp/1.0"})

        if r.status_code != 200:
            return {"error": "Fallo en la API", "detalle": r.text}

        resultados = r.json()

        if not resultados:
            return {"error": "Localidad no encontrada"}

        loc = resultados[0]
        lat = loc.get("lat")
        lon = loc.get("lon")

        if not lat or not lon:
            return {"error": "La localidad no tiene coordenadas"}

        return {
            "lat": lat,
            "lng": lon
        }

    except Exception as e:
        return {"error": f"Excepción consultando la API: {str(e)}"}

def buscar_direccion_completa(provincia: str, municipio: str, localidad: str, calle: str, altura: str, url: str):
    """
    Busca coordenadas y dirección completa usando la URL que le pases.
    Si la URL es de Nominatim, hace forward geocoding (calle + altura → lat/lon).
    """
    try:
        # Construir la dirección completa
        direccion_completa = f"{calle} {altura}, {localidad}, {municipio}, {provincia}, Argentina"

        # Parámetros según Nominatim
        params = {
            "q": direccion_completa,
            "format": "json",
            "limit": 1
        }

        r = requests.get(url, params=params, timeout=5, headers={"User-Agent": "MiApp/1.0"})

        if r.status_code != 200:
            return {"error": "Fallo en la API", "detalle": r.text}

        resultados = r.json()

        if not resultados:
            return {"error": "dirección no encontrada"}

        d = resultados[0]

        # extraer lat y lon
        lat = d.get("lat")
        lon = d.get("lon")

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

        return {
            "lat": lat,
            "lng": lon,
            "calle": calle_nominatim
        }

    except Exception as e:
        return {"error": "Falló la API", "detalle": str(e)}

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

def decodificar_logo(logo_base64: str) -> bytes:
    """Decodifica un string Base64 a bytes y valida tamaño."""
    try:
        logo_bytes = base64.b64decode(logo_base64)
        if len(logo_bytes) > MAX_LOGO_SIZE:
            maximo = MAX_LOGO_SIZE // 1024
            raise HTTPException(status_code=400, detail=f"Logo demasiado grande (máximo {maximo} KB)")
        return logo_bytes
    except Exception:
        raise HTTPException(status_code=400, detail="Logo inválido")

def codificar_logo(logo_bytes: bytes) -> str:
    """Codifica bytes a Base64 para enviar al frontend."""
    if not logo_bytes:
        return None
    return base64.b64encode(logo_bytes).decode("utf-8")

def validar_logo_png(logo_bytes: bytes):
    """Valida que los bytes correspondan a un PNG."""
    try:
        with Image.open(io.BytesIO(logo_bytes)) as img:
            if img.format != "PNG":
                raise HTTPException(status_code=400, detail="Solo se acepta PNG")
    except Exception:
        raise HTTPException(status_code=400, detail="Logo inválido")