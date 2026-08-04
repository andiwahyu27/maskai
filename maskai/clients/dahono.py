"""MASKAI — Dahono AI client (CR-010 hardened)"""
import logging
import requests
from maskai.config import config

log = logging.getLogger("maskai.dahono")


def claude(messages, max_tokens=500):
    """Claude via Dahono — safe JSON/HTTP handling with separated error boundaries"""
    try:
        r = requests.post(
            f"{config.DAHONO_URL}/chat/completions",
            json={
                "model": "dahono/claude-sonnet-5",
                "messages": messages,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {config.DAHONO_KEY}",
                "Content-Type": "application/json",
            },
            timeout=config.HTTP_TIMEOUT_LONG,
        )
    except requests.Timeout:
        log.error("Claude timeout")
        return None
    except requests.ConnectionError:
        log.error("Claude connection error")
        return None
    except requests.RequestException as exc:
        log.error("Claude request failed error_type=%s", type(exc).__name__)
        return None

    if not 200 <= r.status_code < 300:
        log.warning("Claude HTTP failure status=%s", r.status_code)
        return None

    try:
        body = r.json()
    except ValueError:
        log.error("Claude invalid JSON")
        return None

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log.error("Claude malformed response")
        return None

    if not isinstance(content, str) or not content.strip():
        log.error("Claude empty content")
        return None

    return content
