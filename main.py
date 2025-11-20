from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from routers import usuario, empresa
from core.auxiliares import limpiar_tokens_expirados
from core.variables import FRONTEND_URL
from core.database import engine, Base # engine es la conexión a la base de datos, y Base es la clase base de los modelos.

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

scheduler = BackgroundScheduler()
scheduler.add_job(limpiar_tokens_expirados, "interval", hours=24)
scheduler.start()

'''
# Limpieza periódica de los turnos vencidos de la tabla Turno. Si están vencidos hace una semana o más, se pasan a la tabla Hsitorial
scheduler = BackgroundScheduler()
scheduler.add_job(limpiar_turnos_vencidos, "interval", hours=24)
scheduler.start()
'''

'uvicorn main:app --reload --port 8000'

'http://127.0.0.1:8000/docs'

'https://github.com/agustiina18/pps-proyecto/tree/feat/integracion-backend' # No usar

'https://github.com/Shir07/pps-proyecto2' # usar este y no el de arriba de las chicas

'https://github.com/EduDavMorales/miturno-api'

'https://www.figma.com/design/xMTrz4i0dETO8RwtYvF84y/MiTurno-APP-WEB'

'https://trello.com/b/Hxb6LrqB/proyecto-pps'