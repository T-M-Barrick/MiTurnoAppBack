import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import usuario, empresa, geo, whatsapp
from core.variables import PORT, FRONTEND_URL
from core.database import engine, Base # engine es la conexión a la base de datos, y Base es la clase base de los modelos.
from core.recs import start_scheduler
from core.seed import run_seeds
from core import models

# Creamos la aplicación FastAPI y le da un título que se ve en la documentación automática (/docs).
app = FastAPI(title="Reservas API")

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine) # No sobrescribe ninguna base ni ninguna tabla existente. Tampoco borra registros.

# 🔥 CONFIGURACIÓN CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, # dominio de la pagina web (es el dominio donde está alojado el frontend)
        "http://127.0.0.1:5501", # solo para desarrollo local
    ],
    allow_credentials=True, # necesario para usar cookies
    allow_methods=["*"], # permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"], # permite todos los headers
)

app.include_router(usuario.router)
app.include_router(empresa.router)
app.include_router(geo.router)
app.include_router(whatsapp.router)

start_scheduler()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)

'uvicorn main:app --reload --port 8000'

'http://127.0.0.1:8000/docs'

'https://github.com/agustiina18/pps-proyecto/tree/feat/integracion-backend'

'https://github.com/EduDavMorales/miturno-api'

'https://www.figma.com/design/xMTrz4i0dETO8RwtYvF84y/MiTurno-APP-WEB'

'https://trello.com/b/Hxb6LrqB/proyecto-pps'

'''
REGISTRO USUARIO LISTO VINCULADO
HOME USUARIO LISTO VINCULADO
MIS EMPRESAS LISTO VINCULADO
ACEPTAR INVITACION LISTO VINCULADO
PANEL EMPRESA LISTO VINCULADO
RESERVAR TURNO LISTO VINCULADO
FAVORITOS LISTO VINCULADO
HISTORIAL LISTO VINCULADO
RESTABLECER-PASSWORD LISTO VINCULADO
PERFIL USUARIO LISTO VINCULADO
CONTACTO NO POR AHORA

HOME EMRPESA LISTO VINCULADO
REGISTRO EMPPRESA LISTO VINCULADO
TURNOS EMPRESA LISTO VINCULADO
HISTORIAL EMPRESA LISTO VINCULADO
PERFIL EMPRESA LISTO VINCULADO
MIEMBROS EMPRESA LISTO VINCULADO
'''