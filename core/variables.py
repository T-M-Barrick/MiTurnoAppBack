import os

from dotenv import load_dotenv

# Estados que debe tener el turno para poder ser movido a la tabla Historial
LISTA_PARCIAL_DE_ESTADOS = ['cancelado por usuario', 'cancelado por empresa', 'cumplido', 'no cumplido']

# Esta collation es específica de MySQL 8.0+. Hace que no distinga entre letras con tilde o no y que no distinga tampoco entre mayúsculas y minúsculas
COLLATION_MYSQL_8 = 'utf8mb4_0900_ai_ci'

DIAS_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

GEOREF_URL = "https://apis.datos.gob.ar/georef/api"

load_dotenv() # carga las variables del .env al entorno

PORT = int(os.getenv("PORT", 8000)) # puerto del back. Railway asigna PORT

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL")

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "zaUbBvZNnNWDUhKqBnkDqlQlwrmCmwTu")
DB_HOST = os.getenv("DB_HOST", "mysql-gwzs.railway.internal")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "railway")

DB_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")