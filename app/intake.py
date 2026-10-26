from dataclasses import dataclass
from typing import Any

from app.models import IncomingMessage
from app.store import Store


@dataclass
class IntakeResult:
    reply: str
    lead: dict[str, Any] | None = None


GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}


class IntakeAssistant:
    """Scripted lead qualifier. It avoids inventing prices or service claims."""

    def __init__(self, store: Store, bot_name: str):
        self.store = store
        self.bot_name = bot_name

    def handle(self, message: IncomingMessage) -> IntakeResult:
        text = (message.text or "").strip()
        if not text:
            return IntakeResult("Please send a text message about your project, and I’ll help with the next steps.")

        state = self.store.load(message.platform, message.sender_id) or {"stage": "project"}
        if state.get("stage") == "complete":
            state = {"stage": "project"}

        stage = state.get("stage", "project")
        lower = text.lower().strip(".!?, ")

        if stage == "project":
            if lower in GREETINGS or len(text) < 8:
                reply = f"Hi, I’m {self.bot_name}. What are you looking to build or improve?"
            else:
                state["project"] = text
                state["stage"] = "timeline"
                reply = "Thanks. What timeline are you working toward?"
        elif stage == "timeline":
            state["timeline"] = text
            state["stage"] = "budget"
            reply = "What budget range are you considering? Please include the currency; ‘not sure yet’ is fine."
        elif stage == "budget":
            state["budget"] = text
            state["stage"] = "contact"
            reply = "Thanks. What name and email or phone number should the developer use to follow up?"
        else:
            state["contact"] = text
            state["stage"] = "complete"
            state["platform"] = message.platform
            state["sender_id"] = message.sender_id
            state["conversation_id"] = message.conversation_id
            state["business_id"] = message.business_id
            state["message_id"] = message.message_id
            lead = {
                "platform": message.platform,
                "sender_id": message.sender_id,
                "project": state.get("project", ""),
                "timeline": state.get("timeline", ""),
                "budget": state.get("budget", ""),
                "contact": state.get("contact", ""),
                "conversation_id": message.conversation_id,
            }
            self.store.save(message.platform, message.sender_id, state)
            return IntakeResult(
                "Thanks—I’ve recorded your project details for follow-up. The developer will review them and get back to you.",
                lead=lead,
            )

        self.store.save(message.platform, message.sender_id, state)
        return IntakeResult(reply)
