# Denniskipkoech.dev AI Chatbot — starter

A Python/FastAPI starter for automatically qualifying development-service inquiries from Instagram, Facebook Messenger, WhatsApp, and TikTok, then emailing the lead summary to `denenorr78@gmail.com`.

## Current behavior

This first version is a **scripted lead-intake bot**, not a generative AI responder. It asks for:

1. What the client wants to build or improve
2. Their timeline
3. Their budget and currency ("not sure yet" is accepted)
4. Their name and email/phone for follow-up

It avoids making up service details, prices, or delivery promises. Add approved FAQs and choose an AI provider before enabling open-ended AI answers. The given portfolio URL could not be read during setup, so no site claims have been added.

## Run locally

```bash
cd denniskipkoech-chatbot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env; for development, load it with: set -a && source .env && set +a
uvicorn app.main:app --reload
```

`GET /health` checks both the app and its configured database and returns `{"status":"ok", ...}` only when the database is available. For local development, omit `DATABASE_URL` and the app uses SQLite. Webhook endpoints require valid provider signatures; test signature verification and event parsing before connecting real accounts.

## Deploy to Vercel

Vercel runs this FastAPI app as a Python Function; the existing `app/main.py` entrypoint exports the `app` object it expects. Deploy the project directory as the Vercel project root.

1. Create a managed PostgreSQL database (for example Neon or Supabase) and copy its **pooled** connection URL.
2. Add `DATABASE_URL` and the required platform credentials from `.env.example` to the Vercel project's Environment Variables. Set `APP_ENV=production`.
3. Import the repository in Vercel and deploy. Check `https://<deployment-domain>/health`; it should return HTTP 200.
4. Register the corresponding HTTPS webhook URLs in each platform's developer console and use the matching verify tokens.
5. Send test messages with test accounts before enabling live auto-replies.

Vercel/production startup fails if `DATABASE_URL` is missing, rather than silently creating an ephemeral SQLite database. Use the provider's pooled PostgreSQL URL to avoid exhausting database connections across function instances. Keep local development on SQLite by leaving `DATABASE_URL` unset.

## Webhook routes

- `GET/POST /webhooks/meta` — Meta webhooks for Page-linked Messenger and Instagram Messaging. The Meta app must subscribe to the relevant message fields and use the required account permissions.
- `GET/POST /webhooks/whatsapp` — WhatsApp Business Platform webhook verification and incoming text messages.
- `POST /webhooks/tiktok` — TikTok `im_receive_msg` Business Messaging events, with TikTok signature verification.

All outbound replies are sent only in response to an incoming message. Set channel credentials in environment variables; the app does not send anything until the corresponding tokens and account IDs are configured. Failed reply delivery returns an error so the provider can retry; the saved reply is reused on retry to avoid advancing the intake twice. Missing SMTP settings mean leads are retained in the configured database but no email is sent.

## Credentials and account access

Create the necessary apps and obtain authorization directly in each platform's developer/business console. Never paste access tokens, app secrets, email passwords, or one-time codes into chat or commit them to source control. For Gmail SMTP, use an app password or a mail provider credential. Deploy behind HTTPS and store secrets in the hosting provider's secret manager.

TikTok Business Messaging API access may require account eligibility, developer access, and privacy/security review. WhatsApp replies use the Business Platform/Cloud API. Meta Instagram messaging requires an eligible Professional account; this starter assumes a Page-linked Meta integration.

## Production work still needed

- Configure each platform app, webhook subscription, permissions, and approved business accounts.
- Configure production SMTP if email notifications are needed; without SMTP, lead details remain in the database.
- Add durable email delivery/retries and monitoring/alerting. Webhook response retries are supported, but external delivery can still be repeated if a provider accepted a reply and the app failed before recording success.
- Add a privacy notice, consent/retention policy, access controls for lead records, and a human handoff procedure.
- Provide approved service/FAQ/pricing content before enabling answers beyond intake.
- End-to-end test with test accounts before enabling auto-replies on live pages.

## Tests

```bash
python -m unittest discover -s tests -v
```
