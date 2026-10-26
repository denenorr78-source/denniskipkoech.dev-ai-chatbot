import hashlib
import hmac
import json
import time


def verify_meta_signature(raw_body: bytes, signature_header: str, app_secret: str) -> bool:
    if not app_secret or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))


def verify_tiktok_signature(
    raw_body: bytes,
    signature_header: str,
    app_secret: str,
    max_skew_seconds: int = 300,
    now: int | None = None,
) -> bool:
    if not app_secret or not signature_header:
        return False
    parts: dict[str, str] = {}
    for item in signature_header.split(","):
        key, sep, value = item.strip().partition("=")
        if sep:
            parts[key] = value
    timestamp, received = parts.get("t"), parts.get("s")
    if not timestamp or not received:
        return False
    try:
        issued_at = int(timestamp)
        current = int(time.time()) if now is None else now
    except ValueError:
        return False
    if abs(current - issued_at) > max_skew_seconds:
        return False
    try:
        payload_obj = json.loads(raw_body)
        canonical_body = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    signed = f"{timestamp}.{canonical_body}".encode()
    expected = hmac.new(app_secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)
