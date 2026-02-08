PYDANTIC_ERROR_MAP = {
    # tipos
    "int_parsing": "INVALID_INTEGER",
    "float_parsing": "INVALID_FLOAT",
    "string_type": "INVALID_STRING",
    "bool_parsing": "INVALID_BOOLEAN",

    # requeridos
    "missing": "FIELD_REQUIRED",

    # rangos numéricos
    "greater_than": "VALUE_TOO_SMALL", # significa que debe enviar un valor mayor ya que envió un valor muy pequeño
    "greater_than_equal": "VALUE_TOO_SMALL",
    "less_than": "VALUE_TOO_LARGE",
    "less_than_equal": "VALUE_TOO_LARGE",

    # strings
    "string_too_short": "STRING_TOO_SHORT",
    "string_too_long": "STRING_TOO_LONG",

    # formatos
    "email_parsing": "INVALID_EMAIL",
}

VALIDATORS_CODES_ERROR = [
    "HORA_MULTIPLO_5",
    "INVALID_TIME_RANGE",
    "INVALID_TIME_RANGE_WITH_INTERVALO",
]