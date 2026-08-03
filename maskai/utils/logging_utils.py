"""MASKAI — Secret redaction and safe logging helpers (CR-010)"""
from urllib.parse import urlsplit, urlunsplit


def redact_secret(value: str) -> str:
    """Replace known secrets with ***"""
    if not value:
        return ""
    redacted = str(value)
    from maskai.config import config
    secrets = [config.BOT_TOKEN, config.SUPABASE_KEY, config.DAHONO_KEY]
    for s in secrets:
        if s:
            redacted = redacted.replace(s, "***")
    return redacted


def safe_url_for_log(url: str) -> str:
    """Return URL safe for logging — no token, no query string"""
    safe = redact_secret(url)
    try:
        parts = urlsplit(safe)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except (ValueError, TypeError):
        return safe.split("?")[0][:160]


def safe_body_for_log(text, max_len=80):
    """Truncate response body for safe logging"""
    if not text:
        return ""
    safe = redact_secret(str(text))
    safe = safe[:max_len]
    return safe.replace("\n", " ")
