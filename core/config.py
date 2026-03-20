import os

from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv() # carga las variables de entorno

PORT = int(os.getenv("PORT", 8000)) # puerto del back. Railway asigna PORT

FRONTEND_URL = os.getenv("FRONTEND_URL")
FRONT_VERIFICACTION_EMAIL_PATH = os.getenv("FRONT_VERIFICACTION_EMAIL_PATH")
FRONT_INVITE_EMAIL_PATH = os.getenv("FRONT_INVITE_EMAIL_PATH")
FRONT_RESET_EMAIL_PATH = os.getenv("FRONT_RESET_EMAIL_PATH")

EMAIL = os.getenv("EMAIL")
SERVER_API_KEY_BREVO = os.getenv("SERVER_API_KEY_BREVO")

GMAIL = os.getenv("GMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

DB_URL = os.getenv("DB_URL")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
VERIFY_EMAIL_TOKEN_EXPIRE_HOURS = int(os.getenv("VERIFY_EMAIL_TOKEN_EXPIRE_HOURS", 24))
COOKIE_NAME = os.getenv("COOKIE_NAME")
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True # URLs HTTPS
)