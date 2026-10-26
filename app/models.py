from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingMessage:
    platform: str
    sender_id: str
    text: str
    message_id: str = ""
    conversation_id: str = ""
    business_id: str = ""
    raw: dict[str, Any] | None = None
