import re

def validate_password(password: str) -> None:

    if " " in password:
        raise ValueError("La contraseña no puede contener espacios")

    if not re.search(r"[A-Za-z]", password):
        raise ValueError("La contraseña debe contener al menos una letra")

    if not re.search(r"[0-9]", password):
        raise ValueError("La contraseña debe contener al menos un número")