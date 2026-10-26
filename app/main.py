import json
import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.channels import meta, tiktok, whatsapp
from app.config import settings
from app.emailer import send_lead_email
from app.intake import IntakeAssistant, IntakeResult
from app.models import IncomingMessage
from app.security import verify_meta_signature, verify_tiktok_signature
from app.store import Store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

if (settings.app_env.lower() == "production" or os.getenv("VERCEL") == "1") and not settings.database_url:
    raise RuntimeError("DATABASE_URL must be configured for production and Vercel deployments")

store = Store(settings.database_url or settings.database_path)
assistant = IntakeAssistant(store, settings.bot_name)
app = FastAPI(title=settings.bot_name, version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        store.check()
    except Exception as exc:
        logger.error("Database health check failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "service": settings.bot_name}


def _verify_hub(request: Request, expected_token: str) -> str:
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and expected_token and params.get("hub.verify_token") == expected_token:
        return params.get("hub.challenge", "")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.get("/webhooks/meta")
async def verify_meta(request: Request) -> PlainTextResponse:
    return PlainTextResponse(_verify_hub(request, settings.meta_verify_token))


@app.get("/webhooks/whatsapp")
async def verify_whatsapp(request: Request) -> PlainTextResponse:
    token = settings.whatsapp_verify_token or settings.meta_verify_token
    return PlainTextResponse(_verify_hub(request, token))


async def _process(
    messages: list[IncomingMessage],
    sender: Callable[[IncomingMessage, str], Awaitable[bool]],
) -> None:
    for message in messages:
        if store.is_processed(message.platform, message.message_id):
            continue
        cached_result = store.load_pending_event(message.platform, message.message_id)
        if cached_result:
            result = IntakeResult(reply=cached_result["reply"], lead=cached_result.get("lead"))
        else:
            result = assistant.handle(message)
            store.save_pending_event(
                message.platform,
                message.message_id,
                {"reply": result.reply, "lead": result.lead},
            )
        try:
            sent = await sender(message, result.reply)
        except Exception:
            # Never log message contents, access tokens, or full provider responses.
            logger.exception("Reply delivery failed for channel=%s", message.platform)
            raise HTTPException(status_code=503, detail="Reply delivery failed") from None
        if not sent:
            logger.error("Reply not sent because channel credentials are not configured: %s", message.platform)
            raise HTTPException(status_code=503, detail="Reply delivery is not configured")
        store.mark_processed(message.platform, message.message_id)
        if result.lead:
            emailed = await send_lead_email(result.lead)
            if not emailed:
                logger.warning("Lead captured but email notification is not configured or failed")


@app.post("/webhooks/meta")
async def receive_meta(request: Request) -> dict[str, str]:
    raw = await request.body()
    if not verify_meta_signature(raw, request.headers.get("X-Hub-Signature-256", ""), settings.meta_app_secret):
        raise HTTPException(status_code=401, detail="Invalid Meta webhook signature")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    await _process(meta.parse_meta(payload), meta.send_reply)
    return {"status": "ok"}


@app.post("/webhooks/whatsapp")
async def receive_whatsapp(request: Request) -> dict[str, str]:
    raw = await request.body()
    if not verify_meta_signature(raw, request.headers.get("X-Hub-Signature-256", ""), settings.meta_app_secret):
        raise HTTPException(status_code=401, detail="Invalid Meta webhook signature")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    await _process(whatsapp.parse_whatsapp(payload), whatsapp.send_reply)
    return {"status": "ok"}


@app.post("/webhooks/tiktok")
async def receive_tiktok(request: Request) -> dict[str, str]:
    raw = await request.body()
    signature = request.headers.get("TikTok-Signature", "")
    if not verify_tiktok_signature(
        raw,
        signature,
        settings.tiktok_app_secret,
        settings.tiktok_webhook_max_skew_seconds,
    ):
        raise HTTPException(status_code=401, detail="Invalid TikTok webhook signature")
    try:
        messages = await tiktok.parse_tiktok(raw)
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid TikTok event payload") from exc
    await _process(messages, tiktok.send_reply)
    return {"status": "ok"}
