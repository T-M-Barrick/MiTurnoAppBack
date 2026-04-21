from datetime import datetime

from sqlalchemy.orm import Session

from core import models, exceptions, autenticacion, timezone

def revoke_token(db: Session, jti: str, expires_at: datetime) -> None:

    expires_at = timezone.to_naive_utc(expires_at) # garantía defensiva
    ahora_utc = timezone.to_naive_utc(timezone.now_utc())

    rt = models.Blacklist(jti=jti, expires_at=expires_at, revoked_at=ahora_utc)
    db.add(rt)
    db.commit()

def change_password(db: Session, user: models.Usuario, old_password: str, new_password: str) -> None:

    if old_password == new_password:
        raise exceptions.PasswordInvalidFormatError(field="new_password")

    if not autenticacion.verify_password(old_password, user.hashed_password):
        raise exceptions.PasswordIncorrectError(field="old_password")

    try:
        user.hashed_password = autenticacion.get_password_hash(new_password)
        db.commit()
    except Exception:
        db.rollback()
        raise
