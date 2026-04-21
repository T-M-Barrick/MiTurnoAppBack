PYDANTIC_ERROR_MAP = {
    # ── Tipos básicos ──────────────────────────────────────────────────────────
    "int_parsing":      "INVALID_INTEGER",
    "int_type":         "INVALID_INTEGER",
    "float_parsing":    "INVALID_FLOAT",
    "float_type":       "INVALID_FLOAT",
    "string_type":      "INVALID_STRING",
    "bool_parsing":     "INVALID_BOOLEAN",
    "bool_type":        "INVALID_BOOLEAN",

    # ── Requeridos ─────────────────────────────────────────────────────────────
    "missing":          "FIELD_REQUIRED",
    "none_required":    "FIELD_REQUIRED",

    # ── Rangos numéricos ───────────────────────────────────────────────────────
    "greater_than":         "VALUE_TOO_SMALL",
    "greater_than_equal":   "VALUE_TOO_SMALL",
    "less_than":            "VALUE_TOO_LARGE",
    "less_than_equal":      "VALUE_TOO_LARGE",

    # ── Múltiplo (conint/confloat multiple_of) ─────────────────────────────────
    "multiple_of":      "NOT_MULTIPLE_OF",

    # ── Strings ────────────────────────────────────────────────────────────────
    "string_too_short":         "STRING_TOO_SHORT",
    "string_too_long":          "STRING_TOO_LONG",
    "string_pattern_mismatch":  "INVALID_FORMAT",

    # ── Decimales (condecimal) ─────────────────────────────────────────────────
    "decimal_parsing":      "INVALID_DECIMAL",
    "decimal_max_digits":   "DECIMAL_TOO_MANY_DIGITS",
    "decimal_max_places":   "DECIMAL_TOO_MANY_PLACES",
    "decimal_whole_digits": "DECIMAL_TOO_MANY_DIGITS",

    # ── Fechas y horas ─────────────────────────────────────────────────────────
    "date_parsing":         "INVALID_DATE",
    "date_type":            "INVALID_DATE",
    "time_parsing":         "INVALID_TIME",
    "time_type":            "INVALID_TIME",
    "datetime_parsing":     "INVALID_DATETIME",
    "datetime_type":        "INVALID_DATETIME",

    # ── Listas (conlist) ───────────────────────────────────────────────────────
    "too_short":    "LIST_TOO_SHORT",
    "too_long":     "LIST_TOO_LONG",
    "list_type":    "INVALID_LIST",

    # ── Enum ───────────────────────────────────────────────────────────────────
    "enum":         "INVALID_ENUM_VALUE",

    # ── Formatos ───────────────────────────────────────────────────────────────
    "email_parsing":    "INVALID_EMAIL",
    "url_parsing":      "INVALID_URL",
    "url_too_long":     "STRING_TOO_LONG",
}