from uuid import uuid4
from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt

from core.models import Usuario, Token
from core.variables import SECRET_KEY, ALGORITHM

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
    user = session.query(Usuario).filter_by(email=email).first()
    if not user:
        return None
    if verify_password(password, user.hashed_password):
        return user
    return None

# ------------------ TOKEN JWT ------------------ #
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



# ---------------- RECUPERAR CONTRASEÑA ---------------- #

# ---------------- GENERAR TOKEN ---------------- #
def generate_password_reset_token(session: Session, email: str) -> str:
    user = session.query(Usuario).filter_by(email=email).first()
    if not user:
        raise ValueError("Email no registrado")

    token = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)

    reset_entry = Token(usuario_id=user.id, token=token, expires_at=expires_at)
    session.add(reset_entry)
    session.commit()
    return token

# ---------------- RESETEAR CONTRASEÑA (VÍA MAIL) ---------------- #
def reset_password(session: Session, token: str, new_password: str):

    # Se busca el token en la tabla Token
    token_entry = session.query(Token).filter_by(token=token).first()

    # Se valida que exista y que no haya expirado
    if not token_entry:
        raise ValueError("Token inválido")

    if token_entry.expires_at < datetime.utcnow():
        raise ValueError("Token expirado")
    
    # Se cambia la contraseña del usuario
    user = session.query(Usuario).filter_by(id=token_entry.usuario_id).first()
    user.hashed_password = get_password_hash(new_password)

    # Se borra el token de la base de datos para que no pueda reutilizarse (no reinicia el id)
    session.delete(token_entry)

    # Guardo los cambios
    session.commit()

    return user