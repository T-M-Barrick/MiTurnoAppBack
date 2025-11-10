from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from routers import usuario, empresa
from core.auxiliares import limpiar_tokens_expirados

# Creamos la aplicación FastAPI y le da un título que se ve en la documentación automática (/docs).
app = FastAPI(title="Reservas API")

# 🔥 CONFIGURACIÓN CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",     # Para desarrollo local (por ejemplo Live Server de VSCode)
        "http://127.0.0.1:5500",
        "https://tusitio.com", # dominio de la pagina web (es el dominio donde está alojado el frontend)
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

'from core.database import engine, Base # engine es la conexión a la base de datos, y Base es la clase base de los modelos.'
'Base.metadata.create_all(bind=engine) # Crear tablas en la base de datos'

'uvicorn main:app --reload' 'http://127.0.0.1:8000/docs'

'https://github.com/agustiina18/pps-proyecto/tree/feat/integracion-backend'