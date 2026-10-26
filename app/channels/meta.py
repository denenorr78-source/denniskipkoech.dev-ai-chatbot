from typing import Any

import httpx

from app.config import settings
from app.models import IncomingMessage


def parse_meta(payload: dict[str, Any]) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message") or {}
            sender = (event.get("sender") or {}).get("id")
            text = message.get("text")
            if not sender or not isinstance(text, str) or message.get("is_echo"):
                continue
            messages.append(IncomingMessage(
                platform="meta",
                sender_id=str(sender),
                text=text,
                message_id=str(message.get("mid", "")),
                conversation_id=str(sender),
                raw=event,
            ))
    return messages


async def send_reply(message: IncomingMessage, text: str) -> bool:
    if not settings.meta_page_id or not settings.meta_page_access_token:
        return False
    url = f"https://graph.facebook.com/{settings.meta_graph_api_version}/{settings.meta_page_id}/messages"
    payload = {
        "recipient": {"id": message.sender_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.meta_page_access_token}"},
        )
        response.raise_for_status()
    return True
