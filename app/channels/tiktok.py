import json
import httpx

from app.config import settings
from app.models import IncomingMessage


async def parse_tiktok(raw_body: bytes) -> list[IncomingMessage]:
    payload = json.loads(raw_body)
    if payload.get("event") != "im_receive_msg":
        return []
    content = payload.get("content", {})
    if isinstance(content, str):
        content = json.loads(content)
    text = (content.get("text") or {}).get("body")
    sender = content.get("unique_identifier")
    conversation_id = content.get("conversation_id")
    business_id = payload.get("user_openid") or settings.tiktok_business_id
    if not text or not sender or not conversation_id or not business_id:
        return []
    return [IncomingMessage(
        platform="tiktok",
        sender_id=str(sender),
        text=str(text),
        message_id=str(content.get("message_id", "")),
        conversation_id=str(conversation_id),
        business_id=str(business_id),
        raw=payload,
    )]


async def send_reply(message: IncomingMessage, text: str) -> bool:
    if not settings.tiktok_access_token or not (message.business_id or settings.tiktok_business_id) or not message.conversation_id:
        return False
    payload = {
        "business_id": message.business_id or settings.tiktok_business_id,
        "recipient_type": "CONVERSATION",
        "recipient": message.conversation_id,
        "message_type": "TEXT",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://business-api.tiktok.com/open_api/v1.3/business/message/send/",
            json=payload,
            headers={"Access-Token": settings.tiktok_access_token},
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") not in (None, 0):
            raise RuntimeError(f"TikTok API returned code {result.get('code')}")
    return True
