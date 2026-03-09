ACCIONES_DE_ENVIO_DE_EMAIL = {
    "REGISTER": "registro de usuario",
    "RESET_PASSWORD": "restablecimiento de contraseña",
    "INVITATION": "invitación a empresa",
}

# Estados que debe tener el turno para poder ser eliminado
LISTA_PARCIAL_DE_ESTADOS = ['CANCELADO_POR_USUARIO', 'CANCELADO_POR_EMPRESA', 'CUMPLIDO', 'NO_CUMPLIDO']

DIAS_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# Esta collation es específica de MySQL 8.0+. Hace que no distinga entre letras con tilde o no y que no distinga tampoco entre mayúsculas y minúsculas
COLLATION_MYSQL_8 = 'utf8mb4_0900_ai_ci'

GEOREF_URL = "https://apis.datos.gob.ar/georef/api"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

MAX_LOGO_SIZE = 50 * 1024  # 50 KB

"TURNO_NUEVO_USUARIO"
"TURNO_NUEVO_SUCURSAL"
"RECORDATORIO_USUARIO"
"MIEMBRO_NUEVO_EMPRESA"
"MIEMBRO_NUEVO_SUCURSAL"
"TURNO_CANCELADO_POR_USUARIO"
"TURNO_CANCELADO_POR_SUCURSAL"

NOTIFICACIONES = {

    "TURNO_NUEVO_USUARIO": { # si lo sacó la sucursal para vos
        "title": "Turno confirmado",
        "body": "{nombre_empresa} te reservó un turno para {cuando}",
        "required_metadata": ["turno_id", "nombre_empresa", "cuando"],
    },

    "TURNO_NUEVO_SUCURSAL": { # para front de empresa si lo sacó el cliente
        "title": "Nuevo turno",
        "body": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno en {nombre_sucursal} para {cuando}",
        "required_metadata": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "nombre_sucursal"],
    },

    "TURNO_NUEVO_SUCURSAL": { # para front de sucursal si lo sacó el cliente
        "title": "Nuevo turno",
        "body2": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno para {cuando}",
        "required_metadata2": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando"],
    },

    "TURNO_NUEVO_SUCURSAL": { # para front de empresa con vos como profesional si lo sacó el cliente
        "title": "Nuevo turno",
        "body": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno con vos en {nombre_sucursal} para {cuando}",
        "required_metadata": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "nombre_sucursal", "profesional_id"],
    },

    "TURNO_NUEVO_SUCURSAL": { # para front de sucursal con vos como profesional si lo sacó el cliente
        "title": "Nuevo turno",
        "body2": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno con vos para {cuando}",
        "required_metadata2": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "profesional_id"],
    },

    "RECORDATORIO_USUARIO": {
        "title": "Recordatorio de turno",
        "body": "Recordatorio: tenés un turno en {nombre_empresa} para {cuando}",
        "required_metadata": ["turno_id", "nombre_empresa", "cuando"],
    },

    "MIEMBRO_NUEVO_EMPRESA": {
        "title": "Nuevo miembro en empresa",
        "body": "{usuario_apellido}, {usuario_nombre} se unió a la empresa como {rol}",
        "required_metadata": ["usuario_id", "usuario_apellido", "usuario_nombre", "rol"],
    },

    "MIEMBRO_NUEVO_SUCURSAL": { # para front de empresa
        "title": "Nuevo miembro en sucursal",
        "body": "{usuario_apellido}, {usuario_nombre} se unió a la sucursal {nombre_sucursal} como {rol}",
        "required_metadata": ["usuario_id", "sucursal_id", "usuario_apellido", "usuario_nombre", "nombre_sucursal", "rol"],
    },

    "MIEMBRO_NUEVO_SUCURSAL": { # para front de sucursal
        "title": "Nuevo miembro en sucursal",
        "body": "{usuario_apellido}, {usuario_nombre} se unió a la sucursal como {rol}",
        "required_metadata": ["usuario_id", "usuario_apellido", "usuario_nombre", "rol"],
    },

    "TURNO_CANCELADO_USUARIO": { # si lo canceló la sucursal
        "title": "Turno cancelado",
        "body": "{nombre_empresa} canceló tu turno para {cuando}",
        "required_metadata": ["turno_id", "nombre_empresa", "cuando"],
    },

    "TURNO_CANCELADO_SUCURSAL": { # para front de empresa
        "title": "Turno cancelado",
        "body": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno en {nombre_sucursal} para {cuando}",
        "required_metadata": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "nombre_sucursal"],
    },

    "TURNO_CANCELADO_SUCURSAL": { # para front de sucursal
        "title": "Turno cancelado",
        "body2": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno para {cuando}",
        "required_metadata2": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando"],
    },

    "TURNO_CANCELADO_SUCURSAL": { # para front de empresa con vos como profesional
        "title": "Turno cancelado",
        "body": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno con vos en {nombre_sucursal} para {cuando}",
        "required_metadata": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "nombre_sucursal", "profesional_id"],
    },

    "TURNO_CANCELADO_SUCURSAL": { # para front de sucursal con vos como profesional
        "title": "Turno cancelado",
        "body2": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno con vos para {cuando}",
        "required_metadata2": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "profesional_id"],
    },
}