import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import engine, Base # engine es la conexión a la base de datos, y Base es la clase base de los modelos.
from core.config import PORT, FRONTEND_URL
from seed import ejecutar_seeds
from routers import usuario, auth, empresa, sucursal, invitaciones, geo
from handlers.exceptions import register_exception_handlers
from services.scheduler import start_scheduler

# Creamos la aplicación FastAPI y le da un título que se ve en la documentación automática (/docs).
app = FastAPI(title="Reservas API")

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine) # No sobrescribe ninguna base ni ninguna tabla existente. Tampoco borra registros.
ejecutar_seeds()

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
app.include_router(auth.router)
app.include_router(empresa.router)
app.include_router(sucursal.router)
app.include_router(invitaciones.router)
app.include_router(geo.router)

register_exception_handlers(app)

start_scheduler()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)