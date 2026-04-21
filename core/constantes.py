ACCIONES_DE_ENVIO_DE_EMAIL = {
    "REGISTER": "registro de usuario",
    "RESET_PASSWORD": "restablecimiento de contraseña",
    "INVITATION": "invitación a empresa",
}

# Estados que debe tener el turno para poder ser eliminado
LISTA_PARCIAL_DE_ESTADOS = ['CANCELADO_POR_USUARIO', 'CANCELADO_POR_EMPRESA', 'CUMPLIDO', 'NO_CUMPLIDO']

ROL_MAP = {
    'PROPIETARIO': 'Propietario',
    'GERENTE_EMPRESA': 'Gerente de Empresa',
    'GERENTE_SUCURSAL': 'Gerente de Sucursal',
    'EMPLEADO': 'Empleado',
}

DIAS_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

GEOREF_URL = "https://apis.datos.gob.ar/georef/api"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB

NOTIFICACIONES = {

    "TURNO_NUEVO_USUARIO": { # si lo sacó la sucursal para vos
        "title": "Turno confirmado",
        "body": "{nombre_empresa} te reservó un turno para {cuando}",
        "required_metadata": ["turno_id", "nombre_empresa", "cuando"],
    },

    "TURNO_NUEVO_SUCURSAL": {
        "title": "Nuevo turno",
        "body": {
            # para front de empresa si lo sacó el cliente
            "empresa": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno en la sucursal {nombre_sucursal} para {cuando}",
            # para front de sucursal si lo sacó el cliente
            "sucursal": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno para {cuando}",
            # para front de empresa con vos como profesional si lo sacó el cliente
            "empresa_profesional": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno con vos en la sucursal {nombre_sucursal} para {cuando}",
            # para front de sucursal con vos como profesional si lo sacó el cliente
            "sucursal_profesional": "El cliente {cliente_apellido}, {cliente_nombre} reservó un turno con vos para {cuando}",
        },
        "required_metadata": {
            # para front de empresa si lo sacó el cliente
            "empresa": ["turno_id", "cliente_apellido", "cliente_nombre", "nombre_sucursal", "cuando"],
            # para front de sucursal si lo sacó el cliente
            "sucursal": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando"],
            # para front de empresa con vos como profesional si lo sacó el cliente
            "empresa_profesional": ["turno_id", "cliente_apellido", "cliente_nombre", "nombre_sucursal", "cuando", "profesional_id"],
            # para front de sucursal con vos como profesional si lo sacó el cliente
            "sucursal_profesional": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "profesional_id"],
        },
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

    "MIEMBRO_NUEVO_SUCURSAL": {
        "title": "Nuevo miembro en sucursal",
        "body": {
            # para front de empresa
            "empresa": "{usuario_apellido}, {usuario_nombre} se unió a la sucursal {nombre_sucursal} como {rol}",
            # para front de sucursal
            "sucursal": "{usuario_apellido}, {usuario_nombre} se unió a la sucursal como {rol}",
        },
        "required_metadata": {
            # para front de empresa
            "empresa": ["usuario_id", "usuario_apellido", "usuario_nombre", "nombre_sucursal", "rol"],
            # para front de sucursal
            "sucursal": ["usuario_id", "usuario_apellido", "usuario_nombre", "rol"],
        },
    },

    "TURNO_CANCELADO_USUARIO": { # si lo canceló la sucursal
        "title": "Turno cancelado",
        "body": "{nombre_empresa} canceló tu turno programado para {cuando}",
        "required_metadata": ["turno_id", "nombre_empresa", "cuando"],
    },

    "TURNO_CANCELADO_SUCURSAL": {
        "title": "Turno cancelado",
        "body": {
            # para front de empresa
            "empresa": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno en la sucursal {nombre_sucursal} programado para {cuando}",
            # para front de sucursal
            "sucursal": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno programado para {cuando}",
            # para front de empresa con vos como profesional si lo canceló el cliente
            "empresa_profesional": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno con vos en la sucursal {nombre_sucursal} programado para {cuando}",
            # para front de sucursal con vos como profesional si lo canceló el cliente
            "sucursal_profesional": "El cliente {cliente_apellido}, {cliente_nombre} canceló su turno con vos programado para {cuando}",
        },
        "required_metadata": {
            # para front de empresa
            "empresa": ["turno_id", "cliente_apellido", "cliente_nombre", "nombre_sucursal", "cuando"],
            # para front de sucursal
            "sucursal": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando"],
            # para front de empresa con vos como profesional si lo canceló el cliente
            "empresa_profesional": ["turno_id", "cliente_apellido", "cliente_nombre", "nombre_sucursal", "cuando", "profesional_id"],
            # para front de sucursal con vos como profesional si lo canceló el cliente
            "sucursal_profesional": ["turno_id", "cliente_apellido", "cliente_nombre", "cuando", "profesional_id"],
        },
    },
}