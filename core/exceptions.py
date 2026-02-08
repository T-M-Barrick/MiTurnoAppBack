# ------------------ Domain Errores ------------------ #

class DomainError(Exception):
    status_code = 400
    code = "DOMAIN_ERROR"
    default_message = "Error de dominio"

    def __init__(self, field: str | None = None, **metadata):
        self.field = field
        self.metadata = metadata
        super().__init__(self.code)

# ------------------ Domain User Errores ------------------ #

class UserError(DomainError):
    status_code = 400
    code = "USER_ERROR"
    default_message = "Error de usuario"

class UserNotFoundError(UserError):
    status_code = 404
    code = "USER_NOT_FOUND"
    default_message = "Usuario no encontrado"

class UserEmailNotVerifiedError(UserError):
    status_code = 403
    code = "USER_EMAIL_NOT_VERIFIED"
    default_message = "Debes verificar primero tu correo electrónico para poder acceder a tu cuenta"

# ------------------ Domain Empresa Errores ------------------ #

class EmpresaError(DomainError):
    status_code = 400
    code = "EMPRESA_ERROR"
    default_message = "Error de empresa"

class EmpresaNotFoundError(EmpresaError):
    status_code = 404
    code = "EMPRESA_NOT_FOUND"
    default_message = "Empresa no encontrada"

class EmpresaEmailNotVerifiedError(EmpresaError):
    status_code = 403
    code = "EMPRESA_EMAIL_NOT_VERIFIED"
    default_message = "El correo electrónico de la empresa debe ser verificado antes para continuar"

class EmpresaUserBlockedError(EmpresaError):
    status_code = 403
    code = "EMPRESA_USER_BLOCKED"
    default_message = "Fuise bloqueado por esta empresa"

class EmpresaBlockMiembroError(EmpresaError):
    status_code = 403
    code = "EMPRESA_BLOCK_MIEMBRO"
    default_message = "Una empresa no puede bloquear a un usuario que pertenece a la misma"

class EmpresaAlreadyExistsInFavoritosError(EmpresaError):
    status_code = 409
    code = "EMPRESA_ALREADY_EXISTS_IN_FAVORITOS"
    default_message = "La empresa ya se encuentra en favoritos"

class EmpresaDoesNotExistInFavoritosError(EmpresaError):
    status_code = 404
    code = "EMPRESA_DOES_NOT_EXIST_IN_FAVORITOS"
    default_message = "La empresa no se encuentra en favoritos"

class EmpresaMiembroNotFoundError(EmpresaError):
    status_code = 404
    code = "EMPRESA_MIEMBRO_NOT_FOUND"
    default_message = "Usuario no pertenece a la empresa"

class EmpresaMiembroAlreadyExistsError(EmpresaError):
    status_code = 409
    code = "EMPRESA_MIEMBRO_ALREADY_EXISTS"
    default_message = "El usuario ya es miembro de esta empresa"

class EmpresaServiceNotFoundError(EmpresaError):
    status_code = 404
    code = "EMPRESA_SERVICE_NOT_FOUND"
    default_message = "Servicio no encontrado"

class EmpresaServiceDuplicatedError(EmpresaError):
    status_code = 409
    code = "EMPRESA_SERVICE_DUPLICATED"
    default_message = "No puede haber dos servicios con el mismo nombre y profesional (o sin profesional) para la misma empresa"

class EmpresaPropietarioOutError(EmpresaError):
    status_code = 409
    code = "EMPRESA_PROPIETARIO_OUT"
    default_message = "La empresa no puede quedar sin propietarios"

class EmpresaInvalidSelfRemovalError(EmpresaError):
    code = "EMPRESA_INVALID_SELF_REMOVAL"
    default_message = "No se puede abandonar como miembro a una empresa desde este flujo"

class EmpresaPermissionDeniedError(EmpresaError):
    status_code = 403
    code = "EMPRESA_PERMISSION_DENIED"
    default_message = "Permiso denegado"

class EmpresaUpdateByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_UPDATE_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar datos de la empresa"

class EmpresaServiceViewByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_VIEW_BY_EMPLEADO"
    default_message = "Los empleados no pueden visualizar los servicios"

class EmpresaServiceCreateByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_CREATE_BY_EMPLEADO"
    default_message = "Los empleados no pueden crear servicios"

class EmpresaServiceUpdateByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_UPDATE_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar servicios"

class EmpresaServiceDeleteByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_DELETE_BY_EMPLEADO"
    default_message = "Los empleados no pueden eliminar servicios"

class EmpresaMiembrosViewByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBROS_VIEW_BY_EMPLEADO"
    default_message = "Los empleados no pueden visualizar a los miembros de la empresa"

class EmpresaRolUpdateError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_UPDATE"
    default_message = "Los empleados o gerentes no pueden modificar roles"

class EmpresaRolPropietarioUpdateError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_PROPIETARIO_UPDATE"
    default_message = "El rol de un propietario no puede ser modificado por otros miembros de la empresa"

class EmpresaRolAsignedByGerenteError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_ASIGNED_BY_GERENTE"
    default_message = "Los gerentes solamente pueden asignar el rol de empleado"

class EmpresaRolAsignedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_ASIGNED_BY_EMPLEADO"
    default_message = "Los empleados no pueden asignar roles"

class EmpresaMiembroPropietarioDeleteError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBRO_PROPIETARIO_DELETE"
    default_message = "Los propietarios no pueden ser eliminados por otros miembros de la empresa"

class EmpresaMiembroDeleteByGerenteError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBRO_DELETE_BY_GERENTE"
    default_message = "Los gerentes no pueden eliminar propietarios u otros gerentes"

class EmpresaMiembroDeleteByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBRO_DELETE_BY_EMPLEADO"
    default_message = "Los empleados no pueden eliminar miembros"

class EmpresaUnlockUserByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_UNLOCK_USER_BY_EMPLEADO"
    default_message = "Los empleados no pueden desbloquear usuarios"

# ------------------ Domain Rol Errores ------------------ #

class RolInvalidError(DomainError):
    status_code = 400
    code = "ROL_INVALID"
    default_message = "Rol inválido"

# ------------------ Domain Turno Errores ------------------ #

class TurnoError(DomainError):
    status_code = 400
    code = "TURNO_ERROR"
    default_message = "Error en el turno"

class TurnoNotFoundError(TurnoError):
    status_code = 404
    code = "TURNO_NOT_FOUND"
    default_message = "Turno no encontrado"

class TurnoReservaError(TurnoError):
    status_code = 400
    code = "TURNO_RESERVA"
    default_message = "Error al reservar el turno"

class TurnoSinDisponibilidadError(TurnoReservaError):
    status_code = 409
    code = "TURNO_SIN_DISPONIBILIDAD"
    default_message = "No hay turnos disponibles para este servicio en el día y horario seleccionado"

class TurnoReservaAnticipacionInvalidError(TurnoReservaError):
    status_code = 422
    code = "TURNO_RESERVA_ANTICIPACION_INVALID"
    default_message = "El turno en esta empresa para este servicio debe reservarse con al menos {minutos_minimos} minutos de anticipación"

class TurnoReservaFueraDeRangoError(TurnoReservaError):
    status_code = 422
    code = "TURNO_RESERVA_FUERA_DE_RANGO"
    default_message = "El turno solicitado para este servicio excede el límite máximo de {dias_max} días permitidos por la empresa"

class TurnoReservaDisponibilidadNoConfiguradaError(TurnoReservaError):
    status_code = 422
    code = "TURNO_RESERVA_DISPONIBILIDAD_NO_CONFIGURADA"
    default_message = "No hay disponibilidad configurada para este servicio en el día y horario seleccionado"

class TurnoUserOverlappingAppointmentError(TurnoReservaError):
    status_code = 409
    code = "TURNO_USER_OVERLAPPING_APPOINTMENT"
    default_message = "Tenés un turno pendiente que provoca superposición con el turno seleccionado. Por favor, revisar."

class TurnoProfesionalOverlappingAppointmentError(TurnoReservaError):
    status_code = 409
    code = "TURNO_PROFESIONAL_OVERLAPPING_APPOINTMENT"
    default_message = "El profesional {apellido}, {nombre} ya tiene otro turno en ese horario"

class TurnoUpdateError(TurnoError):
    status_code = 400
    code = "TURNO_UPDATE"
    default_message = "Error al modificar el turno"

class TurnoUpdateInvalidStateError(TurnoUpdateError):
    status_code = 422
    code = "TURNO_UPDATE_INVALID_STATE"
    default_message = "Estado de turno inválido"

class TurnoCancelTimeExpiredError(TurnoUpdateError):
    status_code = 409
    code = "TURNO_CANCEL_TIME_EXPIRED"
    default_message = "No se puede cancelar un turno que ya comenzó o terminó"

class TurnoNotFinishedError(TurnoUpdateError):
    status_code = 409
    code = "TURNO_NOT_FINISHED"
    default_message = "El turno no ha finalizado aún, inténtelo luego"

class TurnoUpdateStateImmutableError(TurnoUpdateError):
    status_code = 409
    code = "TURNO_UPDATE_STATE_IMMUTABLE"
    default_message = "El estado no puede volver a modificarse"

class TurnoCancelByMiembroForbiddenError(TurnoUpdateError):
    status_code = 403
    code = "TURNO_CANCEL_BY_MIEMBRO_FORBIDDEN"
    default_message = "Solo el profesional del servicio o un empleado de rango superior puede cancelar este turno"

class TurnoDeleteError(TurnoError):
    status_code = 400
    code = "TURNO_DELETE"
    default_message = "Error al eliminar el turno"

class TurnoDeleteStateConflictError(TurnoDeleteError):
    status_code = 409
    code = "TURNO_DELETE_STATE_CONFLICT"
    default_message = "Se debe cambiar el estado del turno antes de moverlo al historial"

class TurnoHistorialNotFoundError(TurnoDeleteError):
    status_code = 404
    code = "TURNO_HISTORIAL_NOT_FOUND"
    default_message = "Turno no encontrado en el historial"

# ------------------ Domain Password Errores ------------------ #

class PasswordError(DomainError):
    status_code = 400
    code = "PASSWORD_ERROR"
    default_message = "Error de contraseña"

class ChangePasswordError(PasswordError):
    status_code = 400
    code = "CHANGE_PASSWORD"
    default_message = "Error al cambiar la contraseña"

class PasswordIncorrectError(ChangePasswordError):
    status_code = 401
    code = "PASSWORD_INCORRECT"
    default_message = "Contraseña actual incorrecta"

class PasswordInvalidFormatError(ChangePasswordError):
    status_code = 422
    code = "PASSWORD_INVALID_FORMAT"
    default_message = "La nueva contraseña no puede ser igual a la anterior"

class ForgotPasswordError(PasswordError):
    pass

class ForgotPasswordEmailMismatchError(ForgotPasswordError):
    pass

class ResetPasswordError(PasswordError):
    status_code = 400
    code = "RESET_PASSWORD"
    default_message = "Token inválido o expirado"

class InvalidResetTokenError(ResetPasswordError):
    pass

class ExpiredResetTokenError(ResetPasswordError):
    pass

class ResetOTPError(ResetPasswordError):
    code = "RESET_OTP"
    default_message = "Código inválido o expirado"

# ------------------ Domain Verify Errores ------------------ #

class VerifyEmailInvalidExpiredTokenError(AuthError):
    status_code = 400
    code = "VERIFY_EMAIL_INVALID_EXPIRED_TOKEN"
    default_message = "El enlace de verificación no es válido o ha expirado"

# ------------------ Domain Invitation Errores ------------------ #

class InvitationError(DomainError):
    status_code = 409
    code = "INVITATION_ERROR"
    default_message = "No se pudo completar la invitación"

class InvitationTokenInvalidExpiredError(InvitationError):
    code = "INVITATION_TOKEN_INVALID_EXPIRED"
    default_message = "Token inválido o expirado"

class InvitationUserBlockedError(InvitationError):
    status_code = 403
    code = "INVITATION_USER_BLOCKED"
    default_message = "El usuario debe sacarse de la lista de bloqueados primero, antes de poder convertirlo en miembro de la empresa"

# ------------------ Domain Email Errores ------------------ #

class EmailSendFailedError(DomainError):
    status_code = 503
    code = "EMAIL_SEND_FAILED"
    default_message = "No se pudo enviar el correo"

# ------------------ Domain Timezone Errores ------------------ #

class TimezoneInvalidError(DomainError):
    status_code = 422
    code = "TIMEZONE_INVALID"
    default_message = "La fecha y hora enviada tiene una zona horaria inválida"

# ------------------ Domain Logo Errores ------------------ #

class LogoError(DomainError):
    status_code = 400
    code = "LOGO_ERROR"
    default_message = "Error de logo"

class LogoTooLargeError(LogoError):
    code = "LOGO_TOO_LARGE"
    default_message = "Logo demasiado grande (máximo {maximo} KB)"

class LogoInvalidError(LogoError):
    code = "LOGO_INVALID"
    default_message = "Logo inválido"

class LogoInvalidFormatError(LogoError):
    code = "LOGO_INVALID_FORMAT"
    default_message = "Formato de imagen inválido. Formatos permitidos: {allowed}"

# ------------------ AppSystem Errores ------------------ #

class AppSystemError(Exception):
    status_code = 500
    code = "SYSTEM_ERROR"
    default_message = "Error de sistema"

    def __init__(self, **metadata):
        self.metadata = metadata
        super().__init__(self.code)

# ------------------ AppSystem Auth Errores ------------------ #

class AuthError(AppSystemError):
    status_code = 401
    code = "AUTH_ERROR"
    default_message = "Credenciales inválidas"

class AuthTokenMissingError(AuthError):
    pass

class AuthTokenInvalidExpiredError(AuthError):
    pass

class AuthTokenRevokedError(AuthError):
    pass

class AuthUserNotFoundError(AuthError):
    pass

# ------------------ AppSystem GeoRef Errores ------------------ #

class GeoRefError(AppSystemError):
    status_code = 500
    code = "GEOREF_ERROR"
    default_message = "Error en GeoRef"

class GeoRefNotFoundError(GeoRefError):
    status_code = 404
    code = "GEOREF_NOT_FOUND"
    default_message = "Ubicación no encontrada"

class GeoRefLocalidadNotFoundError(GeoRefNotFoundError):
    code = "GEOREF_LOCALIDAD_NOT_FOUND"
    default_message = "Localidad no encontrada"

class GeoRefDireccionNotFoundError(GeoRefNotFoundError):
    code = "GEOREF_DIRECCION_NOT_FOUND"
    default_message = "Dirección no encontrada"

class GeoRefUnavailableError(GeoRefError):
    status_code = 503
    code = "GEOREF_UNAVAILABLE"
    default_message = "Servicio GeoRef no disponible"

class GeoRefInvalidResponseError(GeoRefError):
    status_code = 502
    code = "GEOREF_INVALID_RESPONSE"
    default_message = "Respuesta inválida del servicio GeoRef"