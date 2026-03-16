from uuid import uuid4
import hashlib
from datetime import datetime, timedelta

from fastapi import Depends, Cookie
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload, selectinload
from jose import JWTError, jwt

from core import models, exceptions, timezone
from core.config import SECRET_KEY, ALGORITHM, COOKIE_NAME
from core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------ FUNCIONES DE HASH ------------------ #
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ------------------ AUTENTICACIÓN ------------------ #
'''La autenticación es el proceso de verificar la identidad de alguien que ya tiene cuenta. Se compara lo 
que ingresa (email + contraseña por ejemplo) con lo que está guardado en la base de datos. Si coincide, recibe el acceso a la cuenta.'''
def authenticate(session: Session, email: str, password: str):

    email_normalizado = models.normalizar_email(email)

    user = session.query(models.Usuario).filter_by(email_normalizado=email_normalizado).first()

    # Definimos contra qué vamos a comparar
    if user:
        target_hash = user.hashed_password
    else:
        # HASH FANTASMA: Un hash real (de una password cualquiera).
        # Para que verify_password tarde lo mismo que si el usuario existiera.
        target_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6L65JG6CwsPKOOuW"

    # Verificamos (esta línea es la que tarda ~500ms SIEMPRE) antes de devolver algo
    es_valido = verify_password(password, target_hash)

    if user and es_valido:
        return user
    
    return None

# Esta función chequea el token. Se usa cuando el usuario hace algo con el back que no sea registrarse o loguearse
def get_current_user(token: str = Cookie(default=None, # token: str = Cookie() le dice a FastAPI: Busca en la request HTTP una cookie llamada como config.COOKIE_NAME y pasala a esta función.
                    alias=COOKIE_NAME), db: Session = Depends(get_db)):

    if token is None:
        raise exceptions.AuthTokenMissingError()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # Acá se chequea si está expirado o no el token
        entity_id = int(payload.get("sub"))
        jti = payload.get("jti")
    except JWTError as e:
        raise exceptions.AuthTokenInvalidExpiredError()

    # Chequeo en DB si está revocado
    if db.query(models.Blacklist).filter(models.Blacklist.jti == jti).first():
        raise exceptions.AuthTokenRevokedError()
    
    # Traer usuario
    user = (
        db.query(models.Usuario)
        .options(
            selectinload(models.Usuario.telefonos),
            joinedload(models.Usuario.direcciones),
            selectinload(models.Usuario.favoritos).joinedload(models.Sucursal.empresa),
            selectinload(models.Usuario.favoritos).selectinload(models.Sucursal.telefonos),
            selectinload(models.Usuario.favoritos).joinedload(models.Sucursal.direccion),
            selectinload(models.Usuario.favoritos).selectinload(models.Sucursal.servicios),
        )
        .filter(models.Usuario.id == entity_id).first()
    )

    if not user:
        raise exceptions.AuthUserNotFoundError()
    
    if not user.email_verificado:
        raise exceptions.UserEmailNotVerifiedError()

    return user

# ------------------ TOKEN JWT ------------------ #
def create_email_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    to_encode.update({"type": "email"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    jti = str(uuid4())
    to_encode.update({"jti": jti})
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])  # convertir a string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ------------------ VERIFICACIONES ------------------ #
def verify_email_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email":
            raise exceptions.VerifyEmailInvalidExpiredTokenError()
        return payload
    except JWTError:
        raise exceptions.VerifyEmailInvalidExpiredTokenError()

# ---------------- RECUPERO DE CONTRASEÑA ---------------- #

# ---------------- VÍA EMAIL ---------------- #

def generate_password_reset_token(session: Session, email: str) -> str:

    email_normalizado = models.normalizar_email(email)

    user = session.query(models.Usuario).filter_by(email_normalizado=email_normalizado).first()

    if not user:
        raise exceptions.UserNotFoundError() # email no registrado

    if not user.email_verificado:
        raise exceptions.UserEmailNotVerifiedError()
    
    token_plano = str(uuid4()) # el que viaja por el mail
    
    # Creamos un hash rápido para la DB (SHA-256)
    # Esto es determinista: el mismo token_plano siempre dará el mismo hash_db
    token_hash_db = hashlib.sha256(token_plano.encode()).hexdigest()

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    expires_at = ahora_utc + timedelta(hours=1)

    try:
        # Borramos cualquier token previo de este usuario para que no se acumulen
        session.query(models.Token).filter(models.Token.usuario_id == user.id).delete()

        reset_entry = models.Token(usuario_id=user.id, token=token_hash_db, created_at=ahora_utc, expires_at=expires_at)

        session.add(reset_entry)
        session.commit()
    except Exception:
        session.rollback()
        raise
    
    return token_plano

def reset_password_email(session: Session, token_plano: str, new_password: str):

    # Hashear el token recibido para poder buscarlo
    # Importante: usar la misma lógica que al generar (sha256 + hexdigest)
    token_hash_db = hashlib.sha256(token_plano.encode()).hexdigest()

    # Se busca el token en la tabla Token
    token_entry = session.query(models.Token).filter_by(token=token_hash_db).first()

    # Se ve que exista y que no haya expirado
    if not token_entry:
        raise exceptions.InvalidResetTokenError()

    ahora_utc = timezone.to_naive_utc(timezone.now_utc())
    if token_entry.expires_at < ahora_utc:

        # Si expiró, lo borramos para limpiar la DB
        try:
            session.delete(token_entry)
            session.commit()
        except Exception:
            session.rollback()
            raise

        raise exceptions.ExpiredResetTokenError()
    
    user = session.query(models.Usuario).filter_by(id=token_entry.usuario_id).first()
    if not user:
        raise exceptions.InvalidResetTokenError()

    try:        
        # Se cambia la contraseña del usuario
        user.hashed_password = get_password_hash(new_password)

        session.delete(token_entry) # se borra el token de la base de datos para que no pueda reutilizarse
        session.commit()
    except Exception:
        session.rollback()
        raise
    
    return user

# ---------------- VÍA TELÉFONO ---------------- #

def generate_password_reset_otp(db: Session, telefono: str, email: str):

    usuario = db.query(models.Usuario).join(models.Telefono).filter(models.Telefono.numero == telefono).first()

    if not usuario:
        raise exceptions.UserNotFoundError()
    
    email_normalizado = models.normalizar_email(email)

    if usuario.email_normalizado != email_normalizado:
        raise exceptions.ForgotPasswordEmailMismatchError()
    
    if not usuario.email_verificado:
        raise exceptions.UserEmailNotVerifiedError()

    try:
        # Invalidar OTPs anteriores
        db.query(models.OTPCode).filter(
            models.OTPCode.usuario_id == usuario.id,
            models.OTPCode.used == False,
        ).update({models.OTPCode.used: True})

        # Generar OTP
        otp = mensajes.generar_otp()

        ahora_utc = timezone.to_naive_utc(timezone.now_utc())

        nuevo_otp = models.OTPCode(
            usuario_id=usuario.id,
            code=otp,
            created_at=ahora_utc,
            expires_at=ahora_utc + timedelta(minutes=2),
            used=False,
        )

        db.add(nuevo_otp)
        db.commit()

        return usuario, otp

    except Exception:
        db.rollback()
        raise

def reset_password_mobile(db: Session, telefono: str, otp: str, new_password: str):

    usuario = db.query(models.Usuario).join(models.Telefono).filter(models.Telefono.numero == telefono).first()

    if not usuario:
        raise exceptions.ResetOTPError(field="otp")

    try:
        ahora_utc = timezone.to_naive_utc(timezone.now_utc())

        otp_entry = db.query(models.OTPCode).filter(
            models.OTPCode.usuario_id == usuario.id,
            models.OTPCode.code == otp,
            models.OTPCode.expires_at > ahora_utc,
            models.OTPCode.used == False,
        ).first()

        if not otp_entry:
            raise exceptions.ResetOTPError(field="otp") # puede ser por invalidez o expiración

        usuario.hashed_password = get_password_hash(new_password)
        otp_entry.used = True

        db.commit()
        return usuario

    except Exception:
        db.rollback()
        raise
