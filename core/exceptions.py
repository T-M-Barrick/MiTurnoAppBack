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
        "Email de usuario registrado pero pendiente de verificación. "
        "Por favor, confirma tu cuenta mediante el enlace enviado a tu correo para poder acceder a ella."
    )

class UserAlreadyExistsError(UserError):
    status_code = 409
    code = "USER_ALREADY_EXISTS"
    default_message = "Ya existe un usuario registrado con ese correo electrónico"

class UserBlockedBySucursalError(UserError):
    status_code = 403
    code = "USER_BLOCKED_BY_SUCURSAL"
    default_message = "Fuiste bloqueado por {nombre_empresa}"

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

class EmpresaMiembroAlreadyExistsInAnySucursalError(EmpresaError):
    status_code = 409
    code = "EMPRESA_MIEMBRO_ALREADY_EXISTS_IN_ANY_SUCURSAL"
    default_message = (
        "No se puede agregar al usuario como miembro de la empresa con un rol global, "
        "debido a que ya es miembro de la sucursal {nombre_sucursal}"
    )

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

class EmpresaMiembroDeleteWithTurnosConfirmadosError(EmpresaError):
    status_code = 409
    code = "EMPRESA_MIEMBRO_DELETE_WITH_TURNOS_CONFIRMADOS"
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

class SucursalDeactivatedError(SucursalError):
    status_code = 404
    code = "SUCURSAL_DEACTIVATED"
    default_message = "Sucursal fuera de servicio"

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

class SucursalReservaExceptionDateServiceError(SucursalError):
    status_code = 409
    code = "SUCURSAL_RESERVA_EXCEPTION_DATE_SERVICE"
    default_message = "La reserva para este servicio en esta fecha se encuentra inhabilitada por: {motivo}"

class SucursalClienteBlockedError(SucursalError):
    status_code = 403
    code = "SUCURSAL_CLIENTE_BLOCKED"
    default_message = "Este cliente se encuentra bloqueado"

class SucursalDeactivateWithTurnosConfirmadosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_DEACTIVATE_WITH_TURNOS_CONFIRMADOS"
    default_message = "No se puede desactivar una sucursal que posee turnos confirmados"

class SucursalMiembroNotFoundError(SucursalError):
    status_code = 404
    code = "SUCURSAL_MIEMBRO_NOT_FOUND"
    default_message = "Usuario no pertenece a la sucursal"

class SucursalMiembroAlreadyExistsError(SucursalError):
    status_code = 409
    code = "SUCURSAL_MIEMBRO_ALREADY_EXISTS"
    default_message = "El usuario ya es miembro de la sucursal"

class SucursalServiceError(SucursalError):
    status_code = 400
    code = "SUCURSAL_SERVICE"
    default_message = "Error de servicio"

class SucursalServiceNotFoundError(SucursalServiceError):
    status_code = 404
    code = "SUCURSAL_SERVICE_NOT_FOUND"
    default_message = "Servicio no encontrado"

class SucursalServiceAlreadyExistsError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_ALREADY_EXISTS"
    default_message = "Ya existe un servicio con ese mismo nombre y profesional (o sin profesional)"

class SucursalServiceRangosFechasError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_RANGOS_FECHAS"
    default_message = "Un servicio debe tener exactamente uno o dos rangos de fechas de vigencia activos"

class SucursalServicePosteriorFechaInicioVigenciaError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_POSTERIOR_FECHA_INICIO_VIGENCIA"
    default_message = "La nueva fecha de inicio del nuevo rango debe ser posterior a la fecha de inicio del rango actual"

class SucursalServiceSuperpuestoError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_SUPERPUESTO"
    default_message = "Los rangos de fechas de vigencia de un mismo servicio no pueden superponerese"

class SucursalServiceDisponibilidadSuperpuestaError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DISPONIBILIDAD_SUPERPUESTA"
    default_message = "Las disponibilidades de un mismo servicio no pueden superponerse en los horarios"

class SucursalServiceUpdateDisponibilidadWithTurnosExistentesError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_UPDATE_DISPONIBILIDAD_WITH_TURNOS_EXISTENTES"
    default_message = (
        "La disponibilidad del día {dia} que cubre los turnos de las {hora} hs "
        "no puede pasar a tener un máximo de {cant_turnos_max} turnos posibles en el mismo horario "
        "debido a que en este momento posee {cant_turnos_actual} turnos confirmados para esta misma hora "
        "en el día de fecha {fecha}"
    )

class SucursalServiceUpdateVigenciaWithTurnosExistentesError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_UPDATE_VIGENCIA_WITH_TURNOS_EXISTENTES"
    default_message = (
        "Las fechas de vigencia del nuevo servicio no pueden reducirse a este nuevo rango de fechas, debido a que en este momento "
        "posee {cant_turnos_actual} turnos confirmados que quedarían fuera"
    )

class SucursalServiceDeleteDisponibilidadWithTurnosExistentesError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DELETE_DISPONIBILIDAD_WITH_TURNOS_EXISTENTES"
    default_message = (
        "La disponibilidad del día {dia} que cubre los turnos de las {hora} hs "
        "no puede eliminarse, debido a que en este momento posee {cant_turnos_actual} turnos confirmados para esta misma hora "
        "en el día de fecha {fecha}"
    )

class SucursalServiceDeleteWithTurnosConfirmadosError(SucursalServiceError):
    status_code = 409
    code = "SUCURSAL_SERVICE_DELETE_WITH_TURNOS_CONFIRMADOS"
    default_message = "No se puede eliminar un servicio o un rango de fechas de vigencia de un servicio que posee turnos confirmados"

class SucursalExceptionDateServiceError(SucursalError):
    status_code = 400
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE"
    default_message = "Error de bloqueos de fechas de un servicio"

class SucursalExceptionDateServiceNotFoundError(SucursalExceptionDateServiceError):
    status_code = 404
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_NOT_FOUND"
    default_message = "Bloqueo de fechas del servicio no encontrado"

class SucursalExceptionDateServiceSuperpuestaError(SucursalExceptionDateServiceError):
    status_code = 409
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_SUPERPUESTA"
    default_message = "Los distintos bloqueos de fechas para un mismo servicio no pueden superponerse en los rangos de fechas de vigencia"

class SucursalExceptionDateServiceCreateWithTurnosExistentesError(SucursalExceptionDateServiceError):
    status_code = 409
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_CREATE_WITH_TURNOS_CONFIRMADOS"
    default_message = "No se puede bloquear fechas de un servicio que poseen turnos confirmados"

class SucursalExceptionDateServiceUpdateWithTurnosExistentesError(SucursalExceptionDateServiceError):
    status_code = 409
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_UPDATE_WITH_TURNOS_CONFIRMADOS"
    default_message = "No se puede modificar bloqueos de fechas de un servicio que poseen turnos confirmados"
    default_message = "No se puede extender el rango de fechas de vigencia para el actual bloqueo debido a que incluiría turnos confirmados"

class SucursalProfesionalConTurnosConfirmadosOutError(SucursalError):
    status_code = 409
    code = "SUCURSAL_PROFESIONAL_CON_TURNOS_CONFIRMADOS_OUT"
    default_message = "No se puede dejar una sucursal que tiene turnos confirmados con vos como profesional"

class SucursalMiembroDeleteWithTurnosConfirmadosError(SucursalError):
    status_code = 409
    code = "SUCURSAL_MIEMBRO_DELETE_WITH_TURNOS_CONFIRMADOS"
    default_message = "Los miembros de una sucursal no pueden ser eliminados si poseen aún turnos confirmados como profesional"

class SucursalMiembroAddError(SucursalError):
    code = "SUCURSAL_MIEMBRO_ADD"
    default_message = "No se puede agregar a un miembro a una sucursal desde este flujo"

class SucursalInvalidSelfRemovalError(SucursalError):
    code = "SUCURSAL_INVALID_SELF_REMOVAL"
    default_message = "No se puede abandonar como miembro a una sucursal desde este flujo"

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

class SucursalServiceViewedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_SERVICE_VIEWED_BY_EMPLEADO"
    default_message = "Los empleados no pueden visualizar los servicios"

class SucursalServiceCreatedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_SERVICE_CREATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden crear servicios"

class SucursalServiceUpdatedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_SERVICE_UPDATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar servicios"

class SucursalServiceDeletedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_SERVICE_DELETED_BY_EMPLEADO"
    default_message = "Los empleados no pueden eliminar servicios"

class SucursalExceptionDateServiceCreatedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_CREATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden bloquear fechas de un servicio"

class SucursalExceptionDateServiceUpdatedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_UPDATED_BY_EMPLEADO"
    default_message = "Los empleados no pueden modificar bloqueos de fechas de un servicio"

class SucursalExceptionDateServiceDeletedByEmpleadoError(SucursalPermissionDeniedError):
    code = "SUCURSAL_EXCEPTION_DATE_SERVICE_DELETED_BY_EMPLEADO"
    default_message = "Los empleados no pueden eliminar bloqueos de fechas de un servicio"

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

class ClienteDeactivateWithTurnosConfirmadosError(ClienteError):
    status_code = 409
    code = "CLIENTE_DEACTIVATE_WITH_TURNOS_CONFIRMADOS"
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

# ------------------ Domain Invitation Errores ------------------ #

class InvitationError(DomainError):
    status_code = 409
    code = "INVITATION_ERROR"
    default_message = "No se pudo completar la invitación"

class InvitationTokenInvalidExpiredError(InvitationError):
    code = "INVITATION_TOKEN_INVALID_EXPIRED"
    default_message = "Token inválido o expirado"

# ------------------ Domain Notification Errores ------------------ #

class NotificationNotFoundError(DomainError):
    status_code = 404
    code = "NOTIFICACION_NOT_FOUND"
    default_message = "Notificación no encontrada"

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

class AuthVerifyEmailInvalidExpiredTokenError(AuthError):
    status_code = 400
    code = "VERIFY_EMAIL_INVALID_EXPIRED_TOKEN"
    default_message = "El enlace de verificación no es válido o ha expirado"

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