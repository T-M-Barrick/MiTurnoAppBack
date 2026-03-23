from datetime import datetime, timedelta
import random

import requests
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from core.config import (
    FRONTEND_URL,
    FRONT_VERIFICACTION_EMAIL_PATH,
    FRONT_INVITE_EMAIL_PATH,
    FRONT_RESET_EMAIL_PATH,
    EMAIL,
    SERVER_API_KEY_BREVO,
)
from core.logger import logger
from core import exceptions, timezone

# Configurar la API Key
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = SERVER_API_KEY_BREVO # clave de Brevo

# Crear cliente
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

SENDER_NAME = "MiTurno"

# ------------------ MAIL DE VERIFICACIÓN DE EMAIL ------------------ #
def send_verification_email(to_email: str, token: str):
    verify_link = FRONTEND_URL + FRONT_VERIFICACTION_EMAIL_PATH + token

    send_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": SENDER_NAME, "email": EMAIL},
        template_id=12345,  # ID de la plantilla que creaste en Brevo
        params={
            "verify_link": verify_link
        }
    )

    try:
        api_instance.send_transac_email(send_email)
    except ApiException as e:
        logger.error("Error enviando correo: %s", e)
        raise exceptions.EmailSendFailedError()

# ------------------ MAIL DE INVITACIÓN ------------------ #
def send_invite_email(to_email: str, token: str, empresa_nombre: str, rol: str):
    invite_link = FRONTEND_URL + FRONT_INVITE_EMAIL_PATH + token

    send_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": SENDER_NAME, "email": EMAIL},
        template_id=12345,  # ID de la plantilla que creaste en Brevo
        params={
            "empresa_nombre": empresa_nombre,
            "rol": rol,
            "invite_link": invite_link
        }
    )

    try:
        api_instance.send_transac_email(send_email)
    except ApiException as e:
        logger.error("Error enviando correo: %s", e)
        raise exceptions.EmailSendFailedError() from e

# ------------------ MAIL PARA RESETEO DE CONTRASEÑA ------------------ #
def send_reset_email(to_email: str, token: str):
    reset_link = FRONTEND_URL + FRONT_RESET_EMAIL_PATH + token

    send_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": SENDER_NAME, "email": EMAIL},
        template_id=12345,  # ID de la plantilla que creaste en Brevo
        params={
            "reset_link": reset_link
        }
    )

    try:
        api_instance.send_transac_email(send_email)
    except ApiException as e:
        logger.error("Error enviando correo: %s", e)
        raise exceptions.EmailSendFailedError()

# ------------------ MAIL PARA LUEGO DE CANCELACIÓN ------------------ #
def send_turno_cancelado_email(
    to_email: str,
    us_emp_nombre: str,
    fecha_hora_utc: datetime,
    servicio: str,
    motivo: str | None,
):

    fecha_hora_utc = timezone.ensure_utc(fecha_hora_utc) # garantía defensiva

    fecha_hora_local = timezone.utc_to_local(fecha_hora_utc) # convertimos a horario local para el usuario

    fecha = fecha_hora_local.strftime("%d/%m/%Y")
    hora = fecha_hora_local.strftime("%H:%M")
    
    motivo = motivo.strip() if motivo else None

    send_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": SENDER_NAME, "email": EMAIL},
        template_id=12345,  # ID de la plantilla que creaste en Brevo
        params={
            "us_emp_nombre": us_emp_nombre,
            "fecha": fecha,
            "hora": hora,
            "servicio": servicio,
            "motivo": motivo
        }
    )

    try:
        api_instance.send_transac_email(send_email)
    except ApiException as e:
        logger.error("Error enviando correo: %s", e)
        raise exceptions.EmailSendFailedError() from e

def generar_otp():
    return str(random.randint(100000, 999999))
'''
from twilio.rest import Client

client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_TOKEN)

def enviar_sms(to_number: str, mensaje: str):
    """
    Envía un SMS a un número dado usando Twilio.

    Args:
        to_number (str): número del destinatario, con prefijo internacional
        mensaje (str): texto del mensaje
    """
    try:
        message = client_twilio.messages.create(
            body=mensaje,
            from_=TWILIO_TELEFONO,
            to=to_number
        )
        return to_number
    except Exception as e:
        logger.error(f"Error al enviar SMS a {to_number}: {e}")
        return None

TEMPLATE_OTP = "otp_reset"

def enviar_whatsapp(to_number, message):
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": "to_number",
        "type": "text",
        "text": {"body": message}
    }

    return requests.post(url, headers=headers, json=data).json()

def enviar_whatsapp_template(to_number, template_name, variables):
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": "to_number",
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": var} for var in variables
                    ]
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def enviar_otp_whatsapp(numero, nombre, codigo):
    # Reutilizamos la función genérica
    return enviar_whatsapp_template(
        to=numero,
        template_name=TEMPLATE_OTP,
        variables=[nombre, codigo]
    )
'''

'''
Plantilla OTP de WPP:
Hola {{1}}, aquí está tu código para restablecer tu contraseña:
*{{2}}*
Vence en 2 minutos.
'''