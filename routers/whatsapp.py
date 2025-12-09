from fastapi import APIRouter, Request

router = APIRouter()

VERIFY_TOKEN = "token_miturno_9443"

@router.get("/webhook_whatsapp")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return "Token incorrecto"

@router.post("/webhook_whatsapp")
async def receive_webhook(request: Request):
    data = await request.json()
    print("Webhook recibido:", data)
    return {"status": "ok"}
