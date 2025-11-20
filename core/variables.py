import os

from dotenv import load_dotenv

# Estados que debe tener el turno para poder ser movido a la tabla Historial
LISTA_PARCIAL_DE_ESTADOS = ['cancelado por usuario', 'cancelado por empresa', 'cumplido', 'no cumplido']

# Esta collation es específica de MySQL 8.0+. Hace que no distinga entre letras con tilde o no y que no distinga tampoco entre mayúsculas y minúsculas
COLLATION_MYSQL_8 = 'utf8mb4_0900_ai_ci'

DIAS_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

GEOREF_URL = "https://apis.datos.gob.ar/georef/api"

load_dotenv() # carga las variables del .env al entorno

DATABASE_URL = os.getenv("DATABASE_URL")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")