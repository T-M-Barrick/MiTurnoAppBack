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
    default_message = (
        "Email de usuario registrado pero pendiente de verificación. Por favor, confirma tu cuenta mediante el enlace enviado a tu correo para poder acceder a ella."
    )

class UserAlreadyExistsError(UserError):
    status_code = 409
    code = "USER_ALREADY_EXISTS"
    default_message = "Ya existe un usuario registrado con ese correo electrónico"

class UserBlockedBySucursalError(UserError):
    status_code = 403
    code = "USER_BLOCKED_BY_SUCURSAL"
    default_message = "Fuiste bloqueado por {nombre}"

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
    default_message = (
        "Email de empresa registrado pero pendiente de verificación. Por favor, confirma tu cuenta mediante el enlace enviado a tu correo para poder acceder a ella."
    )

class EmpresaAlreadyExistsError(EmpresaError):
    status_code = 409
    code = "EMPRESA_ALREADY_EXISTS"
    default_message = "Ya existe una empresa registrada con ese correo electrónico"

class EmpresaHasNoSucursalError(EmpresaError):
    status_code = 404
    code = "EMPRESA_HAS_NO_SUCURSAL"
    default_message = "La empresa no tiene sucursal asociada"

class EmpresaMiembroNotFoundError(EmpresaError):
    status_code = 404
    code = "EMPRESA_MIEMBRO_NOT_FOUND"
    default_message = "Usuario no pertenece a la empresa"

class EmpresaMiembroAlreadyExistsError(EmpresaError):
    status_code = 409
    code = "EMPRESA_MIEMBRO_ALREADY_EXISTS"
    default_message = "El usuario ya es miembro de la empresa"

class EmpresaPropietarioOutError(EmpresaError):
    status_code = 409
    code = "EMPRESA_PROPIETARIO_OUT"
    default_message = "La empresa no puede quedar sin propietarios"

class EmpresaProfesionalConTurnosConfimadosOutError(EmpresaError):
    status_code = 409
    code = "EMPRESA_PROFESIONAL_CON_TURNOS_CONFIRMADOS_OUT"
    default_message = "No se puede dejar una empresa que tiene turnos confirmados con vos como profesional"

class EmpresaInvalidSelfRemovalError(EmpresaError):
    code = "EMPRESA_INVALID_SELF_REMOVAL"
    default_message = "No se puede abandonar como miembro a una empresa desde este flujo"

class EmpresaMiembroDeleteConTurnosConfirmadosError(EmpresaError):
    status_code = 409
    code = "EMPRESA_MIEMBRO_DELETE_CON_TURNOS_CONFIRMADOS"
    default_message = "Los miembros de una empresa no pueden ser eliminados si poseen aún turnos confirmados como profesional"

class EmpresaPermissionDeniedError(EmpresaError):
    status_code = 403
    code = "EMPRESA_PERMISSION_DENIED"
    default_message = "Permiso denegado"

class EmpresaAccessGlobalResourcesForbiddenError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ACCESS_GLOBAL_RESOURCES_FORBIDDEN"
    default_message = "No tenés acceso a los recursos globales de esta empresa"

class EmpresaAccessResourcesForbiddenError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ACCESS_RESOURCES_FORBIDDEN"
    default_message = "No tenés acceso a los recursos de esta empresa"

class EmpresaUpdatedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_UPDATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar datos de la empresa"

class EmpresaServiceViewedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_VIEWED_BY_EMPLEADO"
    default_message = "Los empleados no pueden visualizar los servicios"

class EmpresaServiceCreatedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_CREATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden crear servicios"

class EmpresaServiceUpdatedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_UPDATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar servicios"

class EmpresaServiceDeletedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_SERVICE_DELETED_BY_EMPLEADO"
    default_message = "Los empleados no pueden eliminar servicios"

class EmpresaMiembrosViewedByEmpleadoError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBROS_VIEWED_BY_EMPLEADO"
    default_message = "Los empleados no pueden visualizar a los miembros de la empresa"

class EmpresaRolUpdateError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_UPDATE"
    default_message = "Los roles de los miembros de una empresa solamente pueden ser modificados por miembros de rango superior"

class EmpresaPersonalRolPropietarioUpdateError(EmpresaPermissionDeniedError):
    code = "EMPRESA_PERSONAL_ROL_PROPIETARIO_UPDATE"
    default_message = "Un propietario solo puede degradarse a gerente de empresa"

class EmpresaRolNotAssignedByPropietarioError(EmpresaPermissionDeniedError):
    code = "EMPRESA_ROL_NOT_ASSIGNED_BY_PROPIETARIO"
    default_message = "Solamente los propietarios pueden asignar roles globales de empresa"

class EmpresaMiembroDeleteError(EmpresaPermissionDeniedError):
    code = "EMPRESA_MIEMBRO_DELETE"
    default_message = "Los miembros de una empresa solamente pueden ser eliminados por miembros de rango superior"

# ------------------ Domain Sucursal Errores ------------------ #

class SucursalError(DomainError):
    status_code = 400
    code = "SUCURSAL_ERROR"
    default_message = "Error de sucursal"

class SucursalNotFoundError(SucursalError):
    status_code = 404
    code = "SUCURSAL_NOT_FOUND"
    default_message = "Sucursal no encontrada"

class SucursalAlreadyExistsWithNameError(SucursalError):
    status_code = 409
    code = "SUCURSAL_ALREADY_EXISTS_WITH_NAME"
    default_message = "Ya existe una sucursal con este nombre en esta empresa"

class SucursalAlreadyExistsWithoutNameError(SucursalError):
    status_code = 409
    code = "SUCURSAL_ALREADY_EXISTS_WITHOUT_NAME"
    default_message = "Ya existe una sucursal sin nombre en esta empresa"

class SucursalReservaPublicaInhabilitadaError(SucursalError):
    status_code = 409
    code = "SUCURSAL_RESERVA_PUBLICA_INHABILITADA"
    default_message = "{nombre} no permite reserva de turnos por parte de los usuarios"

class SucursalClienteBlockedError(SucursalError):
    status_code = 403
    code = "SUCURSAL_CLIENTE_BLOCKED"
    default_message = "Este cliente se encuentra bloqueado"

class SucursalDeactivatedError(SucursalError):
    status_code = 404
    code = "SUCURSAL_DEACTIVATED"
    default_message = "Sucursal fuera de servicio"

class SucursalMiembroNotFoundError(SucursalError):
    status_code = 404
    code = "SUCURSAL_MIEMBRO_NOT_FOUND"
    default_message = "Usuario no pertenece a la sucursal"

class SucursalMiembroAlreadyExistsError(SucursalError):
    status_code = 409
    code = "SUCURSAL_MIEMBRO_ALREADY_EXISTS"
    default_message = "El usuario ya es miembro de la sucursal"

class SucursalServiceNotFoundError(SucursalError):
    status_code = 404
    code = "SUCURSAL_SERVICE_NOT_FOUND"
    default_message = "Servicio no encontrado"

class SucursalServiceDuplicatedError(SucursalError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DUPLICATED"
    default_message = "No puede haber dos servicios con el mismo nombre y profesional (o sin profesional) para la misma sucursal de empresa"

class SucursalServiceDisponibilidadSuperpuestaError(SucursalError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DISPONIBILIDAD_SUPERPUESTA"
    default_message = "Las disponibilidades de un mismo servicio no pueden superponerse en los horarios"

class SucursalServiceUpdateDisponibilidadWithTurnosExistentesError(SucursalError):
    status_code = 409
    code = "SUCURSAL_SERVICE_UPDATE_DISPONIBILIDAD_WITH_TURNOS_EXISTENTES"
    default_message = (
        "La disponibilidad del día {dia} que cubre los turnos de las {hora} hs "
        "no puede pasar a tener un máximo de {cant_max} turnos posibles en el mismo horario "
        "debido a que en este momento posee {cant_actual} turnos confirmados para esta misma hora"
    )

class SucursalServiceDeleteDisponibilidadWithTurnosExistentesError(SucursalError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DELETE_DISPONIBILIDAD_WITH_TURNOS_EXISTENTES"
    default_message = (
        "La disponibilidad del día {dia} que cubre los turnos de las {hora} hs "
        "no puede eliminarse debido a que en este momento posee {cant_actual} turnos confirmados para esta misma hora"
    )

class SucursalDeactivateConTurnosConfirmadosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_DEACTIVATE_CON_TURNOS_CONFIRMADOS"
    default_message = "No se puede desactivar una sucursal que posee turnos confirmados"

class SucursalServiceConTurnosConfirmadosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_SERVICE_CON_TURNOS_CONFIRMADOS"
    default_message = "No se puede eliminar un servicio que posee turnos confirmados"

class SucursalProfesionalConTurnosConfirmadosOutError(SucursalError):
    status_code = 409
    code = "SUCURSAL_PROFESIONAL_CON_TURNOS_CONFIRMADOS_OUT"
    default_message = "No se puede dejar una sucursal que tiene turnos confirmados con vos como profesional"

class SucursalMiembroDeleteConTurnosConfirmadosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_MIEMBRO_DELETE_CON_TURNOS_CONFIRMADOS"
    default_message = "Los miembros de una sucursal no pueden ser eliminados si poseen aún turnos confirmados como profesional"

class SucursalMiembroAddError(SucursalError):
    code = "SUCURSAL_MIEMBRO_ADD"
    default_message = "No se puede agregar a un miembro a una sucursal desde este flujo"

class SucursalInvalidSelfRemovalError(SucursalError):
    code = "SUCURSAL_INVALID_SELF_REMOVAL"
    default_message = "No se puede abandonar como miembro a una sucursal desde este flujo"

class SucursalAlreadyExistsInFavoritosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_ALREADY_EXISTS_IN_FAVORITOS"
    default_message = "La sucursal ya se encuentra en favoritos"

class SucursalDoesNotExistInFavoritosError(SucursalError):
    status_code = 404
    code = "SUCURSAL_DOES_NOT_EXIST_IN_FAVORITOS"
    default_message = "La sucursal no se encuentra en favoritos"

class SucursalPermissionDeniedError(SucursalError):
    status_code = 403
    code = "SUCURSAL_PERMISSION_DENIED"
    default_message = "Permiso denegado"

class SucursalCreatedByGerenteEmpresaError(SucursalPermissionDeniedError):
    code = "SUCURSAL_CREATED_BY_GERENTE_EMPRESA"
    default_message = "Los gerentes de empresa no pueden crear sucursales de empresas"

class SucursalAccessResourcesForbiddenError(SucursalPermissionDeniedError):
    code = "SUCURSAL_ACCESS_RESOURCES_FORBIDDEN"
    default_message = "No tenés acceso a los recursos de esta sucursal"

class SucursalDeactivateForbiddenError(SucursalPermissionDeniedError):
    code = "SUCURSAL_DEACTIVATE_FORBIDDEN"
    default_message = "Solamente el propietario de la sucursal puede desactivarla"

class SucursalActivateForbiddenError(SucursalPermissionDeniedError):
    code = "SUCURSAL_ACTIVATE_FORBIDDEN"
    default_message = "Solamente el propietario de la sucursal puede reactivarla"

class SucursalRolAssignedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_ROL_ASSIGNED_BY_EMPLEADO"
    default_message = "Los empleados no pueden asignar roles"

class SucursalRolAssignedByGerenteError(SucursalPermissionDeniedError):
    code = "SUCURSAL_ROL_ASSIGNED_BY_GERENTE"
    default_message = "Los gerentes de sucursales no pueden asignar roles de gerentes"

class SucursalClienteUnlockedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_CLIENTE_UNLOCKED_BY_EMPLEADO"
    default_message = "Los empleados no pueden desbloquear clientes"

# ------------------ Domain Cliente Errores ------------------ #

class ClienteError(SucursalError):
    status_code = 400
    code = "CLIENTE_ERROR"
    default_message = "Error de cliente"

class ClienteNotFoundError(ClienteError):
    status_code = 404
    code = "CLIENTE_NOT_FOUND"
    default_message = "Cliente no encontrado"

class ClienteAlreadyExistsError(ClienteError):
    status_code = 409
    code = "CLIENTE_ALREADY_EXISTS"
    default_message = "Ya existe un cliente registrado con ese correo electrónico en esta sucursal"

class ClienteDeactivateConTurnosConfirmadosError(ClienteError):
    status_code = 409
    code = "CLIENTE_DEACTIVATE_CON_TURNOS_CONFIRMADOS"
    default_message = "No se puede desactivar a un cliente que posee turnos confirmados"

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
    default_message = "El turno solicitado para este servicio excede el límite máximo de {dias_max} días permitidos por esta empresa"

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

class TurnoCanceledByMiembroForbiddenError(TurnoUpdateError):
    status_code = 403
    code = "TURNO_CANCELED_BY_MIEMBRO_FORBIDDEN"
    default_message = "Solo el profesional del servicio o un miembro de la empresa de rango superior puede cancelar este turno"

class TurnoDeleteError(TurnoError):
    status_code = 400
    code = "TURNO_DELETE"
    default_message = "Error al eliminar el turno"

class TurnoDeleteStateConflictError(TurnoDeleteError):
    status_code = 409
    code = "TURNO_DELETE_STATE_CONFLICT"
    default_message = "Se debe cambiar el estado del turno antes de eliminarlo"

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