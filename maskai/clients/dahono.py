"""MASKAI — AI client (OpenCode Go Responses API)"""
import logging, os
import requests

log = logging.getLogger("maskai.ai")


def _get_opencode_key():
    """Read OpenCode key from env or config files"""
    key = os.environ.get("OPENCODE_GO_API_KEY", "").strip()
    if key:
        return key
    for path in ("/home/ubuntu/maskai/.env", os.path.expanduser("~/.hermes/.env")):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("OPENCODE_GO_API_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            return val
        except FileNotFoundError:
            continue
        except OSError as exc:
            log.error("OpenCode key file unavailable error_type=%s", type(exc).__name__)
    return None


def _extract_response_text(body):
    """Extract text from OpenCode Responses API response. Returns str or None."""
    if isinstance(body.get("output_text"), str) and body["output_text"].strip():
        return body["output_text"]
    output = body.get("output", [])
    if isinstance(output, list):
        for item in output:
            for c in item.get("content", []):
                if isinstance(c.get("text"), str) and c["text"].strip():
                    return c["text"]
    return None


def claude(messages, max_tokens=500):
    """AI text via OpenCode Go Responses API"""
    oc_key = _get_opencode_key()
    if not oc_key:
        log.error("No OpenCode API key found")
        return None

    input_items = [
        {"role": m.get("role", "user"), "content": m.get("content", "")}
        for m in messages
    ]

    try:
        r = requests.post(
            "https://opencode.ai/zen/go/v1/responses",
            json={
                "model": "gpt-5.6-luna",
                "input": input_items,
                "max_output_tokens": max_tokens,
                "store": False,
            },
            headers={"Authorization": f"Bearer {oc_key}", "Content-Type": "application/json"},
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

    text = _extract_response_text(body)
    if not text:
        log.error("AI empty response")
        return None

    log.info("OpenCode response received length=%s", len(text))
    return text
