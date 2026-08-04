"""MASKAI — AI client (OpenCode Go)"""
import logging
import requests

log = logging.getLogger("maskai.ai")


def claude(messages, max_tokens=500):
    """AI text via OpenCode Go — works reliably"""
    import os
    oc_key = None
    # Read from env
    for path in ["/home/ubuntu/maskai/.env", os.path.expanduser("~/.hermes/.env")]:
        try:
            with open(path) as f:
                for line in f:
                    if line.startswith("OPENCODE_GO_API_KEY="):
                        oc_key = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            continue
        if oc_key:
            break
    if not oc_key:
        log.error("No OpenCode API key found")
        return None

    try:
        r = requests.post(
            "https://opencode.ai/zen/go/v1/chat/completions",
            json={
                "model": "gpt-5.6-luna",
                "messages": messages,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {oc_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
    except requests.Timeout:
        log.error("AI timeout")
        return None
    except requests.ConnectionError:
        log.error("AI connection error")
        return None
    except requests.RequestException as exc:
        log.error("AI request failed error_type=%s", type(exc).__name__)
        return None

    if not 200 <= r.status_code < 300:
        log.warning("AI HTTP failure status=%s", r.status_code)
        return None

    try:
        body = r.json()
    except ValueError:
        log.error("AI invalid JSON")
        return None

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log.error("AI malformed response")
        return None

    if not isinstance(content, str) or not content.strip():
        log.error("AI empty content")
        return None

    return content
