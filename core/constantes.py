from enum import intEnum

class Rol(IntEnum):
    propietario = 1
    gerente = 2
    empleado = 3

ACCIONES_DE_ENVIO_DE_EMAIL = {
    "REGISTER": "registro de usuario",
    "RESET_PASSWORD": "restablecimiento de contraseña",
    "INVITATION": "invitación a empresa",
}

# Estados que debe tener el turno para poder ser movido a la tabla Historial
LISTA_PARCIAL_DE_ESTADOS = ['CANCELADO_POR_USUARIO', 'CANCELADO_POR_EMPRESA', 'CUMPLIDO', 'NO_CUMPLIDO']

DIAS_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Esta collation es específica de MySQL 8.0+. Hace que no distinga entre letras con tilde o no y que no distinga tampoco entre mayúsculas y minúsculas
COLLATION_MYSQL_8 = 'utf8mb4_0900_ai_ci'

GEOREF_URL = "https://apis.datos.gob.ar/georef/api"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

MAX_LOGO_SIZE = 50 * 1024  # 50 KB