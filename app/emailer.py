import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

from app.config import settings


def _send_sync(lead: dict[str, Any]) -> bool:
    required = (settings.smtp_host, settings.smtp_from, settings.lead_notify_email)
    if not all(required):
        return False

    msg = EmailMessage()
    msg["Subject"] = f"New development inquiry ({lead.get('platform', 'social')})"
    msg["From"] = settings.smtp_from
    msg["To"] = settings.lead_notify_email
    msg.set_content(
        "A new project inquiry was captured.\n\n"
        f"Channel: {lead.get('platform', '')}\n"
        f"Project: {lead.get('project', '')}\n"
        f"Timeline: {lead.get('timeline', '')}\n"
        f"Budget: {lead.get('budget', '')}\n"
        f"Contact: {lead.get('contact', '')}\n"
        f"Sender ID: {lead.get('sender_id', '')}\n"
    )

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    return True


async def send_lead_email(lead: dict[str, Any]) -> bool:
    try:
        return await asyncio.to_thread(_send_sync, lead)
    except (OSError, smtplib.SMTPException):
        return False
