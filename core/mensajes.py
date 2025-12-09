import random

import requests
from twilio.rest import Client

from core.variables import WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, TEMPLATE_LANG, TWILIO_ACCOUNT_SID, TWILIO_TOKEN, TWILIO_TELEFONO

client = Client(TWILIO_ACCOUNT_SID, TWILIO_TOKEN)

def generar_otp():
    return str(random.randint(100000, 999999))

def enviar_sms(to_number: int, mensaje: str):
    """
    Envía un SMS a un número dado usando Twilio.

    Args:
        to_number (int): número del destinatario, sin prefijo internacional
        mensaje (str): texto del mensaje
    """
    try:
        message = client.messages.create(
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
        "to": f"+54{to_number},
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
Plantilla OTP de WPP:
Hola {{1}}, aquí está tu código para restablecer tu contraseña:
*{{2}}*
Vence en 2 minutos.
'''