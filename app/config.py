from dataclasses import dataclass
import os


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    bot_name: str = os.getenv("BOT_NAME", "Denniskipkoech.dev AI Chatbot")
    lead_notify_email: str = os.getenv("LEAD_NOTIFY_EMAIL", "denenorr78@gmail.com")
    database_path: str = os.getenv("DATABASE_PATH", "./data/leads.sqlite3")
    database_url: str = os.getenv("DATABASE_URL", "")

    meta_verify_token: str = os.getenv("META_VERIFY_TOKEN", "")
    meta_app_secret: str = os.getenv("META_APP_SECRET", "")
    meta_page_id: str = os.getenv("META_PAGE_ID", "")
    meta_page_access_token: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    meta_graph_api_version: str = os.getenv("META_GRAPH_API_VERSION", "v25.0")

    whatsapp_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    tiktok_app_secret: str = os.getenv("TIKTOK_APP_SECRET", "")
    tiktok_access_token: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    tiktok_business_id: str = os.getenv("TIKTOK_BUSINESS_ID", "")
    tiktok_webhook_max_skew_seconds: int = int(os.getenv("TIKTOK_WEBHOOK_MAX_SKEW_SECONDS", "300"))

    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "")
    smtp_use_ssl: bool = _bool("SMTP_USE_SSL")


settings = Settings()
