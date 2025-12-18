import random

import requests
from postmarker.core import PostmarkClient

from core.variables import FRONTEND_URL, EMAIL, SERVER_API_TOKEN_POSTMARK

# Se inicializa el cliente con la API Key de Postmark
client_postmark = PostmarkClient(server_token=SERVER_API_TOKEN_POSTMARK)

# ------------------ MAIL DE INVITACIÓN ------------------ #
def send_invite_email(to_email: str, token: str, empresa_nombre: str, rol: str):
    invite_link = f"{FRONTEND_URL}/pages/usuarios/aceptar-invitacion/aceptar-invitacion?token={token}"
    
    html_body = f"""
    <p>Fuiste invitado a unirte a <strong>{empresa_nombre}</strong> como <strong>{rol}</strong>.</p>
    <p>Hacé click aquí para aceptar: <a href="{invite_link}">{invite_link}</a></p>
    """
    
    client.emails.send(
        From=EMAIL,
        To=to_email,
        Subject=f"Invitación a {empresa_nombre}",
        HtmlBody=html_body,
        TextBody=f"Fuiste invitado a {empresa_nombre} como {rol}. Link: {invite_link}"
    )

# ------------------ MAIL PARA RESETEO DE CONTRASEÑA ------------------ #
def send_reset_email(to_email: str, token: str):
    reset_link = f"{FRONTEND_URL}/pages/usuarios/restablecer-password/reset-password.html?token={token}"
    
    subject = "Recuperar contraseña"
    body = f"Para resetear tu contraseña hacé click aquí: {reset_link}"

    client_postmark.emails.send(
        From=EMAIL, # email verificado en Postmark
        To=to_email,
        Subject=subject,
        HtmlBody=body,
        TextBody=body)

# ------------------ MAIL PARA LUEGO DE CANCELACIÓN ------------------ #
def send_turno_cancelado_email(
    to_email: str,
    us_emp_nombre: str,
    fecha_hora: str,
    servicio: str):

    fecha = fecha_hora.strftime("%d/%m/%Y")
    hora = fecha_hora.strftime("%H:%M")

    subject = f"Turno cancelado por {us_emp_nombre}"

    mensaje = f"""
    <p><strong>{us_emp_nombre}</strong> ha cancelado el turno programado
    para el día <strong>{fecha}</strong> a las <strong>{hora}</strong> hs.</p>

    <p><strong>Servicio:</strong> {servicio}</p>

    <p>Muchas gracias por su comprensión.</p>
    """

    html_body = f"""
    <p>Hola,</p>

    {mensaje}

    <p>— Equipo MiTurno</p>
    """

    text_body = f"""
    {us_emp_nombre} ha cancelado el turno programado
    para el día {fecha} a las {hora} hs.

    Servicio: {servicio}

    Muchas gracias por su comprensión.

    — Equipo MiTurno
    """

    client.emails.send(
        From=EMAIL,
        To=to_email,
        Subject=subject,
        HtmlBody=html_body,
        TextBody=text_body
    )

def generar_otp():
    return str(random.randint(100000, 999999))
'''
from twilio.rest import Client

client_twilio = Client(TWILIO_ACCOUNT_SID, TWILIO_TOKEN)

def enviar_sms(to_number: int, mensaje: str):
    """
    Envía un SMS a un número dado usando Twilio.

    Args:
        to_number (int): número del destinatario, sin prefijo internacional
        mensaje (str): texto del mensaje
    """
    try:
        message = client_twilio.messages.create(
            body=mensaje,
            from_=TWILIO_TELEFONO,
            to=f'+54{to_number}'
        )
        return to_number
    except Exception as e:
        print("Error al enviar SMS:", e)
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
        "to": f"+54{to_number}",
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
        "to": f"+54{to_number}",
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