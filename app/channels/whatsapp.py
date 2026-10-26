from typing import Any

import httpx

from app.config import settings
from app.models import IncomingMessage


def parse_whatsapp(payload: dict[str, Any]) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            phone_id = (value.get("metadata") or {}).get("phone_number_id", "")
            for item in value.get("messages", []):
                sender = item.get("from")
                text = (item.get("text") or {}).get("body")
                if not sender or not isinstance(text, str):
                    continue
                messages.append(IncomingMessage(
                    platform="whatsapp",
                    sender_id=str(sender),
                    text=text,
                    message_id=str(item.get("id", "")),
                    conversation_id=str(sender),
                    business_id=str(phone_id),
                    raw=item,
                ))
    return messages


async def send_reply(message: IncomingMessage, text: str) -> bool:
    phone_id = settings.whatsapp_phone_number_id or message.business_id
    if not phone_id or not settings.whatsapp_access_token:
        return False
    url = f"https://graph.facebook.com/{settings.meta_graph_api_version}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.sender_id,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )
        response.raise_for_status()
    return True
